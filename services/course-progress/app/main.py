from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.catalogs import list_catalog_files
from app.clients import ask_ai_assistant, notify_lms
from app.db import get_cursor

app = FastAPI(title="Прохождение курса")

# Разделы курса и разрешённые переходы между ними. Переход в "test" запрещает
# возврат к материалам, пока тест не завершён (is_final_test не проставлен).
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
    topic_id: int
    message: str
    catalog_file: str | None = None


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

    course["topics"] = topics
    course["reference_catalogs"] = list_catalog_files()
    return course


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
