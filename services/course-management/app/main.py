import os
import uuid
from datetime import datetime
from typing import Optional

import psycopg2
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.clients import generate_questions, notify_lms, parse_program_file
from app.db import get_cursor

LEARNING_MATERIALS_DIR = os.getenv("LEARNING_MATERIALS_DIR", "/app/learning_materials")

app = FastAPI(title="Управление курсами")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ManualTopicRequest(BaseModel):
    id_program: int
    name: str


class AssignmentRequest(BaseModel):
    id_employee: int
    id_program: int


class QuestionGenerationRequest(BaseModel):
    id_topic: int
    count: int = 5


class QuestionUpdateRequest(BaseModel):
    question_text: Optional[str] = None
    is_verified: Optional[bool] = None
    answers: Optional[list[dict]] = None


class ProgramCreateRequest(BaseModel):
    name: str
    program_code: str
    time_to_complete: Optional[int] = None  # в часах
    id_type: int = 1


class ProgramUpdateRequest(BaseModel):
    time_to_complete: Optional[int] = None  # в часах


class LiteratureRequest(BaseModel):
    name: str
    link: Optional[str] = None


class BulkAssignmentRequest(BaseModel):
    id_program: int
    id_position: int


class ComplaintResolveRequest(BaseModel):
    is_solved: bool = True


class AnswerUpdateRequest(BaseModel):
    answer_text: str
    is_correct: bool


@app.get("/health")
def health():
    return {"status": "ok", "service": "course-management"}


@app.get("/programs")
def list_programs():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.id_program, p.program_code, p.name, p.time_to_complete,
                   p.is_shown, t.name AS training_type
            FROM program p
            JOIN training_type t ON t.id_type = p.id_type
            ORDER BY p.id_program
            """
        )
        programs = cur.fetchall()

        for program in programs:
            cur.execute(
                "SELECT COUNT(*) AS count FROM topic WHERE id_program = %s",
                (program["id_program"],),
            )
            program["topic_count"] = cur.fetchone()["count"]

    return programs


@app.get("/programs/{program_id}")
def get_program(program_id: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT p.id_program, p.program_code, p.name, p.time_to_complete,
                   p.is_shown, t.name AS training_type
            FROM program p
            JOIN training_type t ON t.id_type = p.id_type
            WHERE p.id_program = %s
            """,
            (program_id,),
        )
        program = cur.fetchone()
        if not program:
            raise HTTPException(status_code=404, detail="Программа не найдена")

        cur.execute(
            "SELECT id_topic, name FROM topic WHERE id_program = %s", (program_id,)
        )
        program["topics"] = cur.fetchall()

        cur.execute(
            """
            SELECT l.id_literature, l.name, l.material_link
            FROM program_literature pl
            JOIN literature l ON l.id_literature = pl.id_literature
            WHERE pl.id_program = %s
            """,
            (program_id,),
        )
        program["literature"] = cur.fetchall()

    return program


@app.post("/programs")
def create_program(payload: ProgramCreateRequest):
    try:
        with get_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO program (id_type, program_code, name, time_to_complete, is_shown)
                VALUES (%s, %s, %s, %s, true) RETURNING id_program
                """,
                (payload.id_type, payload.program_code, payload.name, payload.time_to_complete),
            )
            result = cur.fetchone()
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Программа с таким номером уже существует")

    return {"id_program": result["id_program"]}


@app.put("/programs/{program_id}")
def update_program(program_id: int, payload: ProgramUpdateRequest):
    fields = []
    params = []
    if payload.time_to_complete is not None:
        fields.append("time_to_complete = %s")
        params.append(payload.time_to_complete)

    if not fields:
        raise HTTPException(status_code=400, detail="Нечего обновлять")

    params.append(program_id)
    with get_cursor(commit=True) as cur:
        cur.execute(
            f"UPDATE program SET {', '.join(fields)} WHERE id_program = %s RETURNING id_program",
            params,
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Программа не найдена")

    return {"status": "updated"}


@app.delete("/programs/{program_id}")
def delete_program(program_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM program WHERE id_program = %s RETURNING id_program",
            (program_id,),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Программа не найдена")

    return {"status": "deleted"}


@app.post("/programs/{program_id}/literature")
def add_literature(program_id: int, payload: LiteratureRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO literature (name, material_link) VALUES (%s, %s) "
            "RETURNING id_literature",
            (payload.name, payload.link or ""),
        )
        literature_id = cur.fetchone()["id_literature"]
        cur.execute(
            "INSERT INTO program_literature (id_program, id_literature) VALUES (%s, %s)",
            (program_id, literature_id),
        )

    return {"id_literature": literature_id}


@app.delete("/literature/{literature_id}")
def delete_literature(literature_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM literature WHERE id_literature = %s RETURNING id_literature",
            (literature_id,),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Источник не найден")

    return {"status": "deleted"}


@app.get("/positions")
def list_positions():
    with get_cursor() as cur:
        cur.execute("SELECT id_position, name FROM position ORDER BY id_position")
        return cur.fetchall()


@app.get("/departments")
def list_departments():
    with get_cursor() as cur:
        cur.execute("SELECT id_department, name, full_name FROM department ORDER BY id_department")
        return cur.fetchall()


@app.get("/assignments")
def list_assignments(id_program: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT pos.id_position, pos.name AS position,
                   dep.id_department, dep.name AS department, dep.full_name AS department_full
            FROM program_completion pc
            JOIN employee e ON e.id_employee = pc.id_employee
            JOIN position pos ON pos.id_position = e.id_position
            LEFT JOIN department dep ON dep.id_department = e.id_department
            WHERE pc.id_program = %s
            """,
            (id_program,),
        )
        return cur.fetchall()


@app.post("/assignments/bulk")
async def bulk_assign(payload: BulkAssignmentRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_employee FROM employee WHERE id_position = %s",
            (payload.id_position,),
        )
        employees = cur.fetchall()

        cur.execute(
            "SELECT name FROM program WHERE id_program = %s",
            (payload.id_program,),
        )
        program = cur.fetchone()

    created = 0
    notified_employee_ids: list[int] = []
    with get_cursor(commit=True) as cur:
        for employee in employees:
            cur.execute(
                "SELECT 1 FROM program_completion WHERE id_employee = %s AND id_program = %s",
                (employee["id_employee"], payload.id_program),
            )
            if cur.fetchone():
                continue
            cur.execute(
                """
                INSERT INTO program_completion (id_employee, id_program, start_date, end_date)
                VALUES (%s, %s, %s, NULL)
                """,
                (employee["id_employee"], payload.id_program, datetime.utcnow()),
            )
            created += 1
            notified_employee_ids.append(employee["id_employee"])

    if program:
        for employee_id in notified_employee_ids:
            await notify_lms(employee_id, f'Вам назначен курс «{program["name"]}»')

    return {"status": "assigned", "employees_assigned": created}


@app.delete("/assignments/bulk")
def bulk_unassign(id_program: int, id_position: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            DELETE FROM program_completion pc
            USING employee e
            WHERE pc.id_employee = e.id_employee
              AND pc.id_program = %s
              AND e.id_position = %s
              AND pc.end_date IS NULL
            RETURNING pc.id_program_completion
            """,
            (id_program, id_position),
        )
        deleted = cur.fetchall()

    return {"status": "unassigned", "count": len(deleted)}


@app.get("/complaints")
def list_complaints(is_solved: Optional[bool] = None):
    query = """
        SELECT c.id_complaint, c.id_question, c.complaint_text, c.is_solved,
               q.question_text
        FROM complaint c
        JOIN question q ON q.id_question = c.id_question
    """
    params: tuple = ()
    if is_solved is not None:
        query += " WHERE c.is_solved = %s"
        params = (is_solved,)
    query += " ORDER BY c.id_complaint DESC"

    with get_cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


@app.put("/complaints/{complaint_id}/resolve")
def resolve_complaint(complaint_id: int, payload: ComplaintResolveRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE complaint SET is_solved = %s WHERE id_complaint = %s "
            "RETURNING id_complaint",
            (payload.is_solved, complaint_id),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Жалоба не найдена")

    return {"status": "updated"}


@app.delete("/topics/{topic_id}")
def delete_topic(topic_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM topic WHERE id_topic = %s RETURNING id_topic",
            (topic_id,),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Тема не найдена")

    return {"status": "deleted"}


@app.post("/topics/{topic_id}/materials")
async def upload_material(topic_id: int, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Допустимы только PPTX-файлы")

    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM topic WHERE id_topic = %s", (topic_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Тема не найдена")

    os.makedirs(LEARNING_MATERIALS_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    with open(os.path.join(LEARNING_MATERIALS_DIR, stored_name), "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO learning_material (id_topic, file_link) VALUES (%s, %s) "
            "RETURNING id_learning_material",
            (topic_id, stored_name),
        )
        material_id = cur.fetchone()["id_learning_material"]

    return {"id_learning_material": material_id, "file_link": stored_name, "original_name": file.filename}


@app.delete("/materials/{material_id}")
def delete_material(material_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM learning_material WHERE id_learning_material = %s RETURNING file_link",
            (material_id,),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Материал не найден")

    try:
        os.remove(os.path.join(LEARNING_MATERIALS_DIR, result["file_link"]))
    except OSError:
        pass

    return {"status": "deleted"}


@app.post("/topics/manual")
def add_topic_manual(payload: ManualTopicRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO topic (id_program, name) VALUES (%s, %s) RETURNING id_topic",
            (payload.id_program, payload.name),
        )
        result = cur.fetchone()

    return {"id_topic": result["id_topic"], "name": payload.name}


@app.post("/programs/parse-file")
async def parse_program(file: UploadFile = File(...)):
    """Прогоняет загруженный DOCX программы через ai-generation и возвращает
    темы/литературу/часы для автозаполнения формы — ничего не пишет в БД."""
    content = await file.read()
    try:
        structure = await parse_program_file(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось разобрать файл: {exc}")

    return structure


@app.post("/assignments")
async def assign_course(payload: AssignmentRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT name FROM program WHERE id_program = %s",
            (payload.id_program,),
        )
        program = cur.fetchone()

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO program_completion (id_employee, id_program, start_date, end_date)
            VALUES (%s, %s, %s, NULL) RETURNING id_program_completion
            """,
            (payload.id_employee, payload.id_program, datetime.utcnow()),
        )
        result = cur.fetchone()

    if program:
        await notify_lms(payload.id_employee, f'Вам назначен курс «{program["name"]}»')

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


@app.post("/questions/generate")
async def generate_topic_questions(payload: QuestionGenerationRequest):
    with get_cursor() as cur:
        cur.execute("SELECT id_topic FROM topic WHERE id_topic = %s", (payload.id_topic,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Тема не найдена")

        cur.execute(
            "SELECT file_link FROM learning_material WHERE id_topic = %s "
            "ORDER BY id_learning_material LIMIT 1",
            (payload.id_topic,),
        )
        material = cur.fetchone()
        if not material:
            raise HTTPException(status_code=400, detail="У темы нет загруженного материала для генерации вопросов")

        previous_questions = _previous_questions_for_topic(cur, payload.id_topic)

    material_path = os.path.join(LEARNING_MATERIALS_DIR, material["file_link"])
    try:
        generated = await generate_questions(material_path, previous_questions, payload.count)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось сгенерировать вопросы: {exc}")

    created_questions = []
    with get_cursor(commit=True) as cur:
        for item in generated:
            cur.execute(
                "INSERT INTO question (id_topic, question_text, is_verified) "
                "VALUES (%s, %s, false) RETURNING id_question",
                (payload.id_topic, item["question_text"]),
            )
            question_id = cur.fetchone()["id_question"]

            answers = []
            for idx, option_text in enumerate(item["options"]):
                is_correct = idx == item["correct_option"]
                cur.execute(
                    "INSERT INTO answer (id_question, answer_text, is_correct) "
                    "VALUES (%s, %s, %s) RETURNING id_answer",
                    (question_id, option_text, is_correct),
                )
                answers.append(
                    {
                        "id_answer": cur.fetchone()["id_answer"],
                        "answer_text": option_text,
                        "is_correct": is_correct,
                    }
                )

            created_questions.append(
                {"id_question": question_id, "question_text": item["question_text"], "answers": answers}
            )

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
        if payload.answers is None:
            raise HTTPException(status_code=400, detail="Нечего обновлять")

    if payload.answers is not None:
        if not payload.answers:
            raise HTTPException(status_code=400, detail="У вопроса должен быть хотя бы один ответ")

        correct_count = sum(1 for answer in payload.answers if answer.get("is_correct"))
        if correct_count != 1:
            raise HTTPException(status_code=400, detail="У вопроса должен быть ровно один правильный ответ")

    params.append(question_id)
    with get_cursor(commit=True) as cur:
        if fields:
            cur.execute(
                f"UPDATE question SET {', '.join(fields)} WHERE id_question = %s RETURNING id_question",
                params,
            )
            result = cur.fetchone()
        else:
            cur.execute("SELECT id_question FROM question WHERE id_question = %s", (question_id,))
            result = cur.fetchone()

        if payload.answers is not None:
            cur.execute(
                "SELECT id_answer FROM answer WHERE id_question = %s ORDER BY id_answer",
                (question_id,),
            )
            existing_answers = cur.fetchall()
            existing_ids = [row["id_answer"] for row in existing_answers]
            payload_ids = [answer["id_answer"] for answer in payload.answers]
            if existing_ids != payload_ids:
                raise HTTPException(status_code=400, detail="Набор ответов вопроса не совпадает с текущим")

            for answer in payload.answers:
                cur.execute(
                    "UPDATE answer SET answer_text = %s, is_correct = %s WHERE id_answer = %s",
                    (answer["answer_text"], answer["is_correct"], answer["id_answer"]),
                )

    if not result:
        raise HTTPException(status_code=404, detail="Вопрос не найден")

    return {"status": "updated"}


@app.put("/answers/{answer_id}")
def update_answer(answer_id: int, payload: AnswerUpdateRequest):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE answer SET answer_text = %s, is_correct = %s WHERE id_answer = %s "
            "RETURNING id_answer",
            (payload.answer_text, payload.is_correct, answer_id),
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Ответ не найден")

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
