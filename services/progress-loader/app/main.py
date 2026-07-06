from typing import Optional

from fastapi import FastAPI, HTTPException

from app.db import get_cursor

app = FastAPI(title="Загрузка данных по прохождениям курсов")


@app.get("/health")
def health():
    return {"status": "ok", "service": "progress-loader"}


@app.get("/program-completions")
def list_program_completions(employee_id: Optional[int] = None):
    query = """
        SELECT pc.id_program_completion, pc.id_employee, pc.id_program,
               p.name AS program_name, pc.start_date, pc.end_date
        FROM program_completion pc
        JOIN program p ON p.id_program = pc.id_program
    """
    params: tuple = ()
    if employee_id is not None:
        query += " WHERE pc.id_employee = %s"
        params = (employee_id,)
    query += " ORDER BY pc.start_date DESC"

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return rows


@app.get("/program-completions/{completion_id}")
def get_program_completion(completion_id: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT pc.id_program_completion, pc.id_employee, pc.id_program,
                   p.name AS program_name, pc.start_date, pc.end_date
            FROM program_completion pc
            JOIN program p ON p.id_program = pc.id_program
            WHERE pc.id_program_completion = %s
            """,
            (completion_id,),
        )
        completion = cur.fetchone()

        if not completion:
            raise HTTPException(status_code=404, detail="Прохождение курса не найдено")

        cur.execute(
            """
            SELECT ms.id_learning_material, lm.file_link, ms.is_read
            FROM material_study ms
            JOIN learning_material lm ON lm.id_learning_material = ms.id_learning_material
            WHERE ms.id_program_completion = %s
            """,
            (completion_id,),
        )
        completion["materials"] = cur.fetchall()

        cur.execute(
            """
            SELECT tc.id_test_completion, tc.id_answer, tc.is_final_test,
                   a.is_correct, a.id_question
            FROM test_completion tc
            JOIN answer a ON a.id_answer = tc.id_answer
            WHERE tc.id_program_completion = %s
            """,
            (completion_id,),
        )
        completion["test_answers"] = cur.fetchall()

    return completion
