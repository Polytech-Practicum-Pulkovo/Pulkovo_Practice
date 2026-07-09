import os
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.catalogs import CATALOGS_DIR, list_catalog_files
from app.clients import generate_chat_answer, generate_questions, notify_lms
from app.db import get_cursor

LEARNING_MATERIALS_DIR = os.getenv("LEARNING_MATERIALS_DIR", "/app/learning_materials")

app = FastAPI(title="Прохождение курса")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECTIONS = ("materials", "test", "results")

# Лимит времени на прохождение любого теста (промежуточного и итогового).
TEST_DURATION_SECONDS = 45 * 60
TEST_QUESTION_COUNT = 15


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


class StartTestSessionRequest(BaseModel):
    id_program_completion: int
    id_topic: int | None = None
    is_final_test: bool = False


@app.get("/health")
def health():
    return {"status": "ok", "service": "course-progress"}


def _session_seconds_remaining(session: dict) -> int:
    elapsed = (datetime.utcnow() - session["started_at"]).total_seconds()
    return max(0, int(session["duration_seconds"] - elapsed))


def _session_payload(session: dict, seconds_remaining: int) -> dict:
    # started_at хранится как наивный UTC datetime — явно помечаем это "Z",
    # иначе браузер разберёт строку как локальное время и таймер съедет.
    return {
        "active": True,
        "id_program_completion": session["id_program_completion"],
        "id_topic": session["id_topic"],
        "is_final_test": session["is_final_test"],
        "started_at": session["started_at"].isoformat() + "Z",
        "duration_seconds": session["duration_seconds"],
        "seconds_remaining": seconds_remaining,
    }


@app.get("/employees/{employee_id}/test-session")
def get_test_session(employee_id: int):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM test_session WHERE id_employee = %s", (employee_id,))
        session = cur.fetchone()

    if not session:
        return {"active": False}

    remaining = _session_seconds_remaining(session)
    if remaining <= 0:
        with get_cursor(commit=True) as cur:
            cur.execute("DELETE FROM test_session WHERE id_employee = %s", (employee_id,))
        return {"active": False}

    return _session_payload(session, remaining)


@app.post("/employees/{employee_id}/test-session/start")
async def start_test_session(employee_id: int, payload: StartTestSessionRequest):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM test_session WHERE id_employee = %s", (employee_id,))
        existing = cur.fetchone()

    if existing:
        remaining = _session_seconds_remaining(existing)
        if remaining > 0:
            is_same = (
                existing["id_program_completion"] == payload.id_program_completion
                and existing["id_topic"] == payload.id_topic
                and existing["is_final_test"] == payload.is_final_test
            )
            if not is_same:
                raise HTTPException(
                    status_code=409,
                    detail="У вас уже есть незавершённый тест — сначала завершите его",
                )
            return _session_payload(existing, remaining)

    if payload.is_final_test:
        with get_cursor() as cur:
            cur.execute(
                "SELECT 1 FROM program_completion WHERE id_program_completion = %s",
                (payload.id_program_completion,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Курс не найден")
    else:
        with get_cursor() as cur:
            cur.execute("SELECT 1 FROM topic WHERE id_topic = %s", (payload.id_topic,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Тема не найдена")

            cur.execute(
                "SELECT COUNT(*) AS count FROM question WHERE id_topic = %s",
                (payload.id_topic,),
            )
            question_count = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT 1
                FROM test_completion tc
                JOIN answer a ON a.id_answer = tc.id_answer
                JOIN question q ON q.id_question = a.id_question
                WHERE tc.id_program_completion = %s AND q.id_topic = %s AND tc.is_final_test = false
                LIMIT 1
                """,
                (payload.id_program_completion, payload.id_topic),
            )
            has_previous_attempt = cur.fetchone() is not None

        if has_previous_attempt:
            await _replenish_topic_questions(payload.id_topic, generate_count=TEST_QUESTION_COUNT)
        elif question_count < TEST_QUESTION_COUNT:
            await _replenish_topic_questions(
                payload.id_topic,
                generate_count=TEST_QUESTION_COUNT - question_count,
            )

    duration = TEST_DURATION_SECONDS
    started_at = datetime.utcnow()

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO test_session
                (id_employee, id_program_completion, id_topic, is_final_test, started_at, duration_seconds)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_employee) DO UPDATE SET
                id_program_completion = EXCLUDED.id_program_completion,
                id_topic = EXCLUDED.id_topic,
                is_final_test = EXCLUDED.is_final_test,
                started_at = EXCLUDED.started_at,
                duration_seconds = EXCLUDED.duration_seconds
            """,
            (employee_id, payload.id_program_completion, payload.id_topic, payload.is_final_test, started_at, duration),
        )

    return _session_payload(
        {
            "id_program_completion": payload.id_program_completion,
            "id_topic": payload.id_topic,
            "is_final_test": payload.is_final_test,
            "started_at": started_at,
            "duration_seconds": duration,
        },
        duration,
    )


@app.delete("/employees/{employee_id}/test-session")
def clear_test_session(employee_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM test_session WHERE id_employee = %s", (employee_id,))
    return {"status": "cleared"}


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
                SELECT COUNT(*) AS answered, COUNT(*) FILTER (WHERE a.is_correct) AS correct
                FROM test_completion tc
                JOIN answer a ON a.id_answer = tc.id_answer
                JOIN question q ON q.id_question = a.id_question
                WHERE tc.id_program_completion = %s AND q.id_topic = %s AND tc.is_final_test = false
                  AND tc.submitted_at = (
                      SELECT MAX(tc2.submitted_at)
                      FROM test_completion tc2
                      JOIN answer a2 ON a2.id_answer = tc2.id_answer
                      JOIN question q2 ON q2.id_question = a2.id_question
                      WHERE tc2.id_program_completion = %s AND q2.id_topic = %s AND tc2.is_final_test = false
                  )
                """,
                (completion_id, topic["id_topic"], completion_id, topic["id_topic"]),
            )
            attempt = cur.fetchone()
            if attempt["answered"]:
                # Неотвеченные (в т.ч. из-за истечения времени) вопросы считаются неверными.
                percent = round(100 * attempt["correct"] / TEST_QUESTION_COUNT)
                topic["progress_percent"] = percent
                topic["status"] = "passed" if percent >= 80 else "in_progress"
            else:
                topic["progress_percent"] = 0
                topic["status"] = "not_started"

    course["topics"] = topics
    course["reference_catalogs"] = list_catalog_files()
    return course


async def _replenish_topic_questions(topic_id: int, generate_count: int = 5) -> None:
    """Догенерирует новые вопросы темы через ai-generation и сохраняет их в БД."""

    with get_cursor() as cur:
        cur.execute(
            "SELECT file_link FROM learning_material WHERE id_topic = %s "
            "ORDER BY id_learning_material LIMIT 1",
            (topic_id,),
        )
        material = cur.fetchone()
        if not material:
            return

        previous_questions = _previous_questions_for_topic(cur, topic_id)

    material_path = os.path.join(LEARNING_MATERIALS_DIR, material["file_link"])
    try:
        generated = await generate_questions(material_path, previous_questions, generate_count)
    except httpx.HTTPError:
        return

    with get_cursor(commit=True) as cur:
        for item in generated:
            cur.execute(
                "INSERT INTO question (id_topic, question_text, is_verified) "
                "VALUES (%s, %s, false) RETURNING id_question",
                (topic_id, item["question_text"]),
            )
            question_id = cur.fetchone()["id_question"]
            for idx, option_text in enumerate(item["options"]):
                cur.execute(
                    "INSERT INTO answer (id_question, answer_text, is_correct) "
                    "VALUES (%s, %s, %s)",
                    (question_id, option_text, idx == item["correct_option"]),
                )


def _previous_questions_for_topic(cur, topic_id: int) -> list[dict]:
    """Собирает уже существующие вопросы темы в формате для дедупликации в ai-generation."""

    cur.execute("SELECT id_question, question_text FROM question WHERE id_topic = %s", (topic_id,))
    existing = cur.fetchall()

    previous = []
    for q in existing:
        cur.execute(
            "SELECT answer_text, is_correct FROM answer WHERE id_question = %s",
            (q["id_question"],),
        )
        answers = cur.fetchall()
        previous.append(
            {
                "question_text": q["question_text"],
                "correct_answers": [a["answer_text"] for a in answers if a["is_correct"]],
                "incorrect_answers": [a["answer_text"] for a in answers if not a["is_correct"]],
            }
        )
    return previous


def _load_topic_questions(cur, topic_id: int, limit: int = TEST_QUESTION_COUNT) -> list[dict]:
    """Возвращает последние вопросы темы, которые используются в тесте."""

    cur.execute(
        """
        SELECT id_question, question_text, is_verified
        FROM question
        WHERE id_topic = %s
        ORDER BY id_question DESC
        LIMIT %s
        """,
        (topic_id, limit),
    )
    questions = list(reversed(cur.fetchall()))

    for question in questions:
        cur.execute(
            "SELECT id_answer, answer_text FROM answer WHERE id_question = %s",
            (question["id_question"],),
        )
        question["answers"] = cur.fetchall()

    return questions


def _load_topic_last_attempt(
    cur, completion_id: int, topic_id: int, question_ids: list[int]
) -> dict | None:
    """Возвращает результаты последней попытки только по текущему набору вопросов."""

    if not question_ids:
        return None

    cur.execute(
        """
        SELECT a.id_question, tc.id_answer, a.is_correct
        FROM test_completion tc
        JOIN answer a ON a.id_answer = tc.id_answer
        JOIN question q ON q.id_question = a.id_question
        WHERE tc.id_program_completion = %s AND q.id_topic = %s AND q.id_question = ANY(%s) AND tc.is_final_test = false
          AND tc.submitted_at = (
              SELECT MAX(tc2.submitted_at)
              FROM test_completion tc2
              JOIN answer a2 ON a2.id_answer = tc2.id_answer
              JOIN question q2 ON q2.id_question = a2.id_question
              WHERE tc2.id_program_completion = %s AND q2.id_topic = %s AND q2.id_question = ANY(%s) AND tc2.is_final_test = false
          )
        """,
        (completion_id, topic_id, question_ids, completion_id, topic_id, question_ids),
    )
    last_answers = cur.fetchall()
    if not last_answers:
        return None

    correct = sum(1 for a in last_answers if a["is_correct"])
    percent = round(100 * correct / len(question_ids))
    return {
        "percent": percent,
        "passed": percent >= 80,
        "answers": last_answers,
    }


def _load_final_test_questions(cur, id_program: int, per_topic: int = 5) -> list[dict]:
    """Возвращает финальный тест: по последним 5 вопросам для каждой темы программы."""

    cur.execute(
        """
        WITH ranked_questions AS (
            SELECT q.id_question, q.question_text, q.id_topic,
                   ROW_NUMBER() OVER (PARTITION BY q.id_topic ORDER BY q.id_question DESC) AS rn
            FROM question q
            JOIN topic t ON t.id_topic = q.id_topic
            WHERE t.id_program = %s
        )
        SELECT id_question, question_text, id_topic
        FROM ranked_questions
        WHERE rn <= %s
        ORDER BY id_topic, id_question
        """,
        (id_program, per_topic),
    )
    questions = cur.fetchall()

    for question in questions:
        cur.execute(
            "SELECT id_answer, answer_text FROM answer WHERE id_question = %s",
            (question["id_question"],),
        )
        question["answers"] = cur.fetchall()

    return questions


@app.get("/courses/{completion_id}/topics/{topic_id}")
async def get_topic(completion_id: int, topic_id: int, employee_id: int):
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

        questions = _load_topic_questions(cur, topic_id)

        topic["questions"] = questions

        question_ids = [q["id_question"] for q in questions]
        topic["last_attempt"] = _load_topic_last_attempt(cur, completion_id, topic_id, question_ids)

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

        questions = _load_final_test_questions(cur, completion["id_program"])
        question_ids = [q["id_question"] for q in questions]

        cur.execute(
            """
            SELECT a.id_question, tc.id_answer, a.is_correct
            FROM test_completion tc
            JOIN answer a ON a.id_answer = tc.id_answer
            JOIN question q ON q.id_question = a.id_question
            JOIN topic t ON t.id_topic = q.id_topic
            WHERE tc.id_program_completion = %s AND t.id_program = %s AND q.id_question = ANY(%s) AND tc.is_final_test = true
              AND tc.submitted_at = (
                  SELECT MAX(tc2.submitted_at)
                  FROM test_completion tc2
                  JOIN answer a2 ON a2.id_answer = tc2.id_answer
                  JOIN question q2 ON q2.id_question = a2.id_question
                  JOIN topic t2 ON t2.id_topic = q2.id_topic
                  WHERE tc2.id_program_completion = %s AND t2.id_program = %s AND q2.id_question = ANY(%s) AND tc2.is_final_test = true
              )
            """,
            (completion_id, completion["id_program"], question_ids, completion_id, completion["id_program"], question_ids),
        )
        last_answers = cur.fetchall()

    last_attempt = None
    if last_answers and questions:
        # Неотвеченные (в т.ч. из-за истечения времени) вопросы считаются неверными.
        correct = sum(1 for a in last_answers if a["is_correct"])
        percent = round(100 * correct / len(questions))
        last_attempt = {
            "percent": percent,
            "passed": percent >= 80,
            "answers": last_answers,
        }

    return {"questions": questions, "last_attempt": last_attempt}


@app.post("/courses/{completion_id}/final-test/submit")
async def submit_final_test(completion_id: int, payload: SubmitTestRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id_program FROM program_completion WHERE id_program_completion = %s",
            (completion_id,),
        )
        completion = cur.fetchone()
        if not completion:
            raise HTTPException(status_code=404, detail="Курс не найден")

        cur.execute(
            "SELECT id_employee FROM program_completion WHERE id_program_completion = %s",
            (completion_id,),
        )
        employee = cur.fetchone()
        if not employee:
            raise HTTPException(status_code=404, detail="Прохождение курса не найдено")

        questions = _load_final_test_questions(cur, completion["id_program"])
        question_ids = [q["id_question"] for q in questions]

        submitted_at = datetime.utcnow()
        for item in payload.answers:
            if item["id_question"] not in question_ids:
                raise HTTPException(status_code=400, detail="Ответ относится к неизвестному вопросу финального теста")
            cur.execute(
                "INSERT INTO test_completion (id_program_completion, id_answer, is_final_test, submitted_at) "
                "VALUES (%s, %s, true, %s)",
                (completion_id, item["id_answer"], submitted_at),
            )

        cur.execute(
            "SELECT is_correct FROM answer WHERE id_answer = ANY(%s)",
            ([item["id_answer"] for item in payload.answers],),
        )
        graded = cur.fetchall()

        total_questions = len(question_ids)

        # Неотвеченные вопросы (например, из-за истечения времени) считаются неверными:
        # процент считается от общего числа вопросов, а не только от отправленных ответов.
        correct = sum(1 for row in graded if row["is_correct"])
        percent = round(100 * correct / total_questions) if total_questions else 0
        passed = percent >= 80

        # Курс считается завершённым только при успешном прохождении итогового теста.
        if passed:
            cur.execute(
                "UPDATE program_completion SET end_date = %s WHERE id_program_completion = %s",
                (datetime.utcnow(), completion_id),
            )

        cur.execute("DELETE FROM test_session WHERE id_employee = %s", (payload.employee_id,))

    if passed:
        await notify_lms(employee["id_employee"], "Курс успешно завершён")

    return {"percent": percent, "passed": passed}


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


@app.get("/materials/{material_id}/file")
def get_material_file(material_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT file_link FROM learning_material WHERE id_learning_material = %s",
            (material_id,),
        )
        material = cur.fetchone()

    if not material:
        raise HTTPException(status_code=404, detail="Материал не найден")

    path = os.path.join(LEARNING_MATERIALS_DIR, material["file_link"])
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Файл материала не найден")

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=material["file_link"],
    )


@app.post("/courses/{completion_id}/topics/{topic_id}/submit-test")
async def submit_topic_test(completion_id: int, topic_id: int, payload: SubmitTestRequest):
    submitted_at = datetime.utcnow()
    with get_cursor(commit=True) as cur:
        for item in payload.answers:
            cur.execute(
                "INSERT INTO test_completion (id_program_completion, id_answer, is_final_test, submitted_at) "
                "VALUES (%s, %s, %s, %s)",
                (completion_id, item["id_answer"], payload.is_final_test, submitted_at),
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

        cur.execute("SELECT COUNT(*) AS count FROM question WHERE id_topic = %s", (topic_id,))
        total_questions = cur.fetchone()["count"]

        # Неотвеченные вопросы (например, из-за истечения времени) считаются неверными:
        # процент считается от общего числа вопросов, а не только от отправленных ответов.
        correct = sum(1 for row in graded if row["is_correct"])
        percent = round(100 * correct / total_questions) if total_questions else 0
        passed = percent >= 80

        completion = None
        if payload.is_final_test and passed:
            cur.execute(
                "SELECT id_employee FROM program_completion WHERE id_program_completion = %s",
                (completion_id,),
            )
            completion = cur.fetchone()
            cur.execute(
                "UPDATE program_completion SET end_date = %s WHERE id_program_completion = %s",
                (datetime.utcnow(), completion_id),
            )

        cur.execute("DELETE FROM test_session WHERE id_employee = %s", (payload.employee_id,))

    if completion:
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
            "INSERT INTO test_completion (id_program_completion, id_answer, is_final_test, submitted_at) "
            "VALUES (%s, %s, %s, %s) RETURNING id_test_completion",
            (completion_id, payload.id_answer, payload.is_final_test, datetime.utcnow()),
        )
        result = cur.fetchone()

        cur.execute("SELECT is_correct FROM answer WHERE id_answer = %s", (payload.id_answer,))
        answer = cur.fetchone()

        # Курс считается завершённым только при успешном прохождении итогового теста.
        if payload.is_final_test and answer and answer["is_correct"]:
            cur.execute(
                "UPDATE program_completion SET end_date = %s WHERE id_program_completion = %s",
                (datetime.utcnow(), completion_id),
            )

    if payload.is_final_test and answer and answer["is_correct"]:
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
    material_path = None
    if payload.catalog_file:
        candidate = os.path.join(CATALOGS_DIR, payload.catalog_file)
        if os.path.isfile(candidate):
            material_path = candidate

    chat_history = []
    if payload.topic_id is not None:
        with get_cursor() as cur:
            cur.execute(
                "SELECT message_text, ai_response_text FROM request "
                "WHERE id_employee = %s AND id_topic = %s ORDER BY sequence_number",
                (payload.employee_id, payload.topic_id),
            )
            for row in cur.fetchall():
                chat_history.append({"role": "user", "content": row["message_text"]})
                chat_history.append({"role": "assistant", "content": row["ai_response_text"]})

    try:
        answer = await generate_chat_answer(payload.message, chat_history, material_path)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось получить ответ ИИ: {exc}")

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
