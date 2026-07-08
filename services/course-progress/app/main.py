from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.catalogs import list_catalog_files
from app.clients import ask_ai_assistant, notify_lms
from app.db import get_cursor

app = FastAPI(title="Прохождение курса")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECTIONS = ("materials", "test", "results")


class NavigateRequest(BaseModel):
    from_section: str
    to_section: str
    test_in_progress: bool = False


class ResultRequest(BaseModel):
    id_answer: int
    is_final_test: bool = False


class ComplaintRequest(BaseModel):
    id_question: int
    complaint_text: str


class AssistantRequest(BaseModel):
    employee_id: int
    topic_id: int | None = None
    message: str
    catalog_file: str | None = None


class SubmitTestRequest(BaseModel):
    employee_id: int
    answers: list[dict]  # [{"id_question": int, "id_answer": int}, ...]
    is_final_test: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "service": "course-progress"}


@app.get("/courses/{completion_id}")
def get_course(completion_id: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT pc.id_program_completion, pc.id_program, p.name AS program_name,
                   pc.start_date, pc.end_date
            FROM program_completion pc
            JOIN program p ON p.id_program = pc.id_program
            WHERE pc.id_program_completion = %s
            """,
            (completion_id,),
        )
        course = cur.fetchone()
        if not course:
            raise HTTPException(status_code=404, detail="Курс не найден")

        cur.execute(
            "SELECT id_topic, name FROM topic WHERE id_program = %s",
            (course["id_program"],),
        )
        topics = cur.fetchall()

        for topic in topics:
            cur.execute(
                "SELECT id_learning_material, file_link FROM learning_material "
                "WHERE id_topic = %s",
                (topic["id_topic"],),
            )
            topic["materials"] = cur.fetchall()

            cur.execute(
                """
                SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE a.is_correct) AS correct
                FROM (
                    SELECT DISTINCT ON (a.id_question) a.id_question, a.is_correct
                    FROM test_completion tc
                    JOIN answer a ON a.id_answer = tc.id_answer
                    JOIN question q ON q.id_question = a.id_question
                    WHERE tc.id_program_completion = %s AND q.id_topic = %s
                      AND tc.is_final_test = false
                    ORDER BY a.id_question, tc.id_test_completion DESC
                ) a
                """,
                (completion_id, topic["id_topic"]),
            )
            attempt = cur.fetchone()
            if attempt["total"]:
                percent = round(100 * attempt["correct"] / attempt["total"])
                topic["progress_percent"] = percent
                topic["status"] = "passed" if percent >= 80 else "in_progress"
            else:
                topic["progress_percent"] = 0
                topic["status"] = "not_started"

    course["topics"] = topics
    course["reference_catalogs"] = list_catalog_files()
    return course


@app.get("/courses/{completion_id}/topics/{topic_id}")
def get_topic(completion_id: int, topic_id: int, employee_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT id_topic, name FROM topic WHERE id_topic = %s", (topic_id,))
        topic = cur.fetchone()
        if not topic:
            raise HTTPException(status_code=404, detail="Тема не найдена")

        cur.execute(
            """
            SELECT lm.id_learning_material, lm.file_link,
                   COALESCE(ms.is_read, false) AS is_read
            FROM learning_material lm
            LEFT JOIN material_study ms
                ON ms.id_learning_material = lm.id_learning_material
               AND ms.id_program_completion = %s
            WHERE lm.id_topic = %s
            """,
            (completion_id, topic_id),
        )
        topic["materials"] = cur.fetchall()

        cur.execute(
            "SELECT id_question, question_text, is_verified FROM question WHERE id_topic = %s",
            (topic_id,),
        )
        questions = cur.fetchall()
        for question in questions:
            cur.execute(
                "SELECT id_answer, answer_text FROM answer WHERE id_question = %s",
                (question["id_question"],),
            )
            question["answers"] = cur.fetchall()
        topic["questions"] = questions

        cur.execute(
            """
            SELECT DISTINCT ON (a.id_question)
                   a.id_question, tc.id_answer, a.is_correct
            FROM test_completion tc
            JOIN answer a ON a.id_answer = tc.id_answer
            JOIN question q ON q.id_question = a.id_question
            WHERE tc.id_program_completion = %s AND q.id_topic = %s AND tc.is_final_test = false
            ORDER BY a.id_question, tc.id_test_completion DESC
            """,
            (completion_id, topic_id),
        )
        last_answers = cur.fetchall()
        if last_answers:
            correct = sum(1 for a in last_answers if a["is_correct"])
            topic["last_attempt"] = {
                "percent": round(100 * correct / len(last_answers)),
                "passed": round(100 * correct / len(last_answers)) >= 80,
                "answers": last_answers,
            }
        else:
            topic["last_attempt"] = None

        cur.execute(
            """
            SELECT id_request, message_text, ai_response_text, sequence_number
            FROM request
            WHERE id_employee = %s AND id_topic = %s
            ORDER BY sequence_number
            """,
            (employee_id, topic_id),
        )
        topic["chat_history"] = cur.fetchall()

    return topic


@app.get("/courses/{completion_id}/final-test")
def get_final_test(completion_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_program FROM program_completion WHERE id_program_completion = %s",
            (completion_id,),
        )
        completion = cur.fetchone()
        if not completion:
            raise HTTPException(status_code=404, detail="Курс не найден")

        cur.execute(
            """
            SELECT q.id_question, q.question_text
            FROM question q
            JOIN topic t ON t.id_topic = q.id_topic
            WHERE t.id_program = %s
            """,
            (completion["id_program"],),
        )
        questions = cur.fetchall()
        for question in questions:
            cur.execute(
                "SELECT id_answer, answer_text FROM answer WHERE id_question = %s",
                (question["id_question"],),
            )
            question["answers"] = cur.fetchall()

        cur.execute(
            """
            SELECT DISTINCT ON (a.id_question)
                   a.id_question, tc.id_answer, a.is_correct
            FROM test_completion tc
            JOIN answer a ON a.id_answer = tc.id_answer
            JOIN question q ON q.id_question = a.id_question
            JOIN topic t ON t.id_topic = q.id_topic
            WHERE tc.id_program_completion = %s AND t.id_program = %s AND tc.is_final_test = true
            ORDER BY a.id_question, tc.id_test_completion DESC
            """,
            (completion_id, completion["id_program"]),
        )
        last_answers = cur.fetchall()

    last_attempt = None
    if last_answers:
        correct = sum(1 for a in last_answers if a["is_correct"])
        last_attempt = {
            "percent": round(100 * correct / len(last_answers)),
            "passed": round(100 * correct / len(last_answers)) >= 80,
            "answers": last_answers,
        }

    return {"questions": questions, "last_attempt": last_attempt}


@app.post("/courses/{completion_id}/final-test/submit")
async def submit_final_test(completion_id: int, payload: SubmitTestRequest):
    with get_cursor(commit=True) as cur:
        for item in payload.answers:
            cur.execute(
                "INSERT INTO test_completion (id_program_completion, id_answer, is_final_test) "
                "VALUES (%s, %s, true)",
                (completion_id, item["id_answer"]),
            )

        cur.execute(
            "SELECT is_correct FROM answer WHERE id_answer = ANY(%s)",
            ([item["id_answer"] for item in payload.answers],),
        )
        graded = cur.fetchall()

        cur.execute(
            "SELECT id_employee FROM program_completion WHERE id_program_completion = %s",
            (completion_id,),
        )
        completion = cur.fetchone()
        cur.execute(
            "UPDATE program_completion SET end_date = %s WHERE id_program_completion = %s",
            (datetime.utcnow(), completion_id),
        )

    correct = sum(1 for row in graded if row["is_correct"])
    percent = round(100 * correct / len(graded)) if graded else 0

    if percent >= 80:
        await notify_lms(completion["id_employee"], "Курс успешно завершён")

    return {"percent": percent, "passed": percent >= 80}


@app.post("/courses/{completion_id}/materials/{material_id}/read")
def mark_material_read(completion_id: int, material_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO material_study (id_program_completion, id_learning_material, is_read)
            VALUES (%s, %s, true)
            ON CONFLICT (id_program_completion, id_learning_material)
            DO UPDATE SET is_read = true
            """,
            (completion_id, material_id),
        )

    return {"status": "read"}


@app.post("/courses/{completion_id}/topics/{topic_id}/submit-test")
async def submit_topic_test(completion_id: int, topic_id: int, payload: SubmitTestRequest):
    with get_cursor(commit=True) as cur:
        for item in payload.answers:
            cur.execute(
                "INSERT INTO test_completion (id_program_completion, id_answer, is_final_test) "
                "VALUES (%s, %s, %s)",
                (completion_id, item["id_answer"], payload.is_final_test),
            )

        cur.execute(
            """
            SELECT a.is_correct
            FROM answer a
            WHERE a.id_answer = ANY(%s)
            """,
            ([item["id_answer"] for item in payload.answers],),
        )
        graded = cur.fetchall()

        if payload.is_final_test:
            cur.execute(
                "SELECT id_employee FROM program_completion WHERE id_program_completion = %s",
                (completion_id,),
            )
            completion = cur.fetchone()
            cur.execute(
                "UPDATE program_completion SET end_date = %s WHERE id_program_completion = %s",
                (datetime.utcnow(), completion_id),
            )

    correct = sum(1 for row in graded if row["is_correct"])
    percent = round(100 * correct / len(graded)) if graded else 0

    if payload.is_final_test and percent >= 80:
        await notify_lms(completion["id_employee"], "Курс успешно завершён")

    return {"percent": percent, "passed": percent >= 80}


@app.post("/courses/{completion_id}/navigate")
def navigate(completion_id: int, payload: NavigateRequest):
    if payload.from_section not in SECTIONS or payload.to_section not in SECTIONS:
        raise HTTPException(status_code=400, detail="Неизвестный раздел курса")

    if payload.test_in_progress and payload.from_section == "test" and payload.to_section != "test":
        raise HTTPException(
            status_code=403,
            detail="Переход запрещён: тест ещё не завершён",
        )

    return {"status": "allowed", "to_section": payload.to_section}


@app.post("/courses/{completion_id}/results")
async def submit_result(completion_id: int, payload: ResultRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_employee FROM program_completion WHERE id_program_completion = %s",
            (completion_id,),
        )
        completion = cur.fetchone()
        if not completion:
            raise HTTPException(status_code=404, detail="Прохождение курса не найдено")

    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO test_completion (id_program_completion, id_answer, is_final_test) "
            "VALUES (%s, %s, %s) RETURNING id_test_completion",
            (completion_id, payload.id_answer, payload.is_final_test),
        )
        result = cur.fetchone()

        if payload.is_final_test:
            cur.execute(
                "UPDATE program_completion SET end_date = %s WHERE id_program_completion = %s",
                (datetime.utcnow(), completion_id),
            )

    if payload.is_final_test:
        await notify_lms(completion["id_employee"], "Курс успешно завершён")

    return {"status": "recorded", "id_test_completion": result["id_test_completion"]}


@app.post("/complaints")
def create_complaint(payload: ComplaintRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO complaint (id_question, complaint_text, is_solved) "
            "VALUES (%s, %s, false) RETURNING id_complaint",
            (payload.id_question, payload.complaint_text),
        )
        result = cur.fetchone()

    return {"status": "created", "id_complaint": result["id_complaint"]}


@app.post("/assistant/ask")
async def ask_assistant(payload: AssistantRequest):
    answer = await ask_ai_assistant(payload.message, payload.topic_id, payload.catalog_file)

    if payload.topic_id is None:
        return {"id_request": None, "answer": answer}

    with get_cursor() as cur:
        cur.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) + 1 AS next_seq FROM request "
            "WHERE id_employee = %s AND id_topic = %s",
            (payload.employee_id, payload.topic_id),
        )
        next_seq = cur.fetchone()["next_seq"]

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO request (id_employee, id_topic, message_text, ai_response_text, sequence_number)
            VALUES (%s, %s, %s, %s, %s) RETURNING id_request
            """,
            (payload.employee_id, payload.topic_id, payload.message, answer, next_seq),
        )
        result = cur.fetchone()

    return {"id_request": result["id_request"], "answer": answer}
