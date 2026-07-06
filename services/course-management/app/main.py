from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.clients import generate_questions, generate_topic_distribution
from app.db import get_cursor

app = FastAPI(title="Управление курсами")


class ManualTopicRequest(BaseModel):
    id_program: int
    name: str


class AiTopicRequest(BaseModel):
    id_program: int
    candidate_topics: list[str]


class AssignmentRequest(BaseModel):
    id_employee: int
    id_program: int


class QuestionGenerationRequest(BaseModel):
    id_topic: int
    count: int = 5


class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = None
    is_verified: Optional[bool] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "course-management"}


@app.post("/topics/manual")
def add_topic_manual(payload: ManualTopicRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO topic (id_program, name) VALUES (%s, %s) RETURNING id_topic",
            (payload.id_program, payload.name),
        )
        result = cur.fetchone()

    return {"id_topic": result["id_topic"], "name": payload.name}


@app.post("/topics/ai-distribution")
async def add_topics_ai(payload: AiTopicRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT name FROM program WHERE id_program = %s", (payload.id_program,)
        )
        program = cur.fetchone()
        if not program:
            raise HTTPException(status_code=404, detail="Программа не найдена")

    distribution = await generate_topic_distribution(program["name"], payload.candidate_topics)

    created = []
    with get_cursor(commit=True) as cur:
        for item in distribution:
            cur.execute(
                "INSERT INTO topic (id_program, name) VALUES (%s, %s) RETURNING id_topic",
                (payload.id_program, item["topic"]),
            )
            created.append({"id_topic": cur.fetchone()["id_topic"], **item})

    return {"topics": created}


@app.post("/assignments")
def assign_course(payload: AssignmentRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO program_completion (id_employee, id_program, start_date, end_date)
            VALUES (%s, %s, %s, NULL) RETURNING id_program_completion
            """,
            (payload.id_employee, payload.id_program, datetime.utcnow()),
        )
        result = cur.fetchone()

    return {"id_program_completion": result["id_program_completion"]}


@app.delete("/assignments/{completion_id}")
def unassign_course(completion_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM program_completion WHERE id_program_completion = %s "
            "RETURNING id_program_completion",
            (completion_id,),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Назначение не найдено")

    return {"status": "deleted"}


@app.post("/questions/generate")
async def generate_topic_questions(payload: QuestionGenerationRequest):
    with get_cursor() as cur:
        cur.execute("SELECT name FROM topic WHERE id_topic = %s", (payload.id_topic,))
        topic = cur.fetchone()
        if not topic:
            raise HTTPException(status_code=404, detail="Тема не найдена")

    generated = await generate_questions(topic["name"], payload.count)

    created_questions = []
    with get_cursor(commit=True) as cur:
        for item in generated:
            cur.execute(
                "INSERT INTO question (id_topic, question_text, is_verified) "
                "VALUES (%s, %s, false) RETURNING id_question",
                (payload.id_topic, item["question_text"]),
            )
            question_id = cur.fetchone()["id_question"]

            for answer in item["answers"]:
                cur.execute(
                    "INSERT INTO answer (id_question, answer_text, is_correct) "
                    "VALUES (%s, %s, %s)",
                    (question_id, answer["answer_text"], answer["is_correct"]),
                )

            created_questions.append({"id_question": question_id, **item})

    return {"questions": created_questions}


@app.get("/questions")
def list_questions(topic_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_question, id_topic, question_text, is_verified FROM question "
            "WHERE id_topic = %s",
            (topic_id,),
        )
        questions = cur.fetchall()

        for question in questions:
            cur.execute(
                "SELECT id_answer, answer_text, is_correct FROM answer WHERE id_question = %s",
                (question["id_question"],),
            )
            question["answers"] = cur.fetchall()

    return questions


@app.put("/questions/{question_id}")
def update_question(question_id: int, payload: QuestionUpdateRequest):
    fields = []
    params = []
    if payload.question_text is not None:
        fields.append("question_text = %s")
        params.append(payload.question_text)
    if payload.is_verified is not None:
        fields.append("is_verified = %s")
        params.append(payload.is_verified)

    if not fields:
        raise HTTPException(status_code=400, detail="Нечего обновлять")

    params.append(question_id)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"UPDATE question SET {', '.join(fields)} WHERE id_question = %s "
            "RETURNING id_question",
            params,
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    return {"status": "updated"}


@app.delete("/questions/{question_id}")
def delete_question(question_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM question WHERE id_question = %s RETURNING id_question",
            (question_id,),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    return {"status": "deleted"}
