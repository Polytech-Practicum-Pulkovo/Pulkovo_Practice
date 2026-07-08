from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_cursor

app = FastAPI(title="Загрузка данных по прохождениям курсов")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _progress_percent(cur, completion_id: int) -> int:
    cur.execute(
        "SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE is_read) AS done "
        "FROM material_study WHERE id_program_completion = %s",
        (completion_id,),
    )
    materials = cur.fetchone()

    cur.execute(
        """
        SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE a.is_correct) AS done
        FROM test_completion tc
        JOIN answer a ON a.id_answer = tc.id_answer
        WHERE tc.id_program_completion = %s
        """,
        (completion_id,),
    )
    tests = cur.fetchone()

    total = materials["total"] + tests["total"]
    done = materials["done"] + tests["done"]
    if total == 0:
        return 0
    return round(100 * done / total)


@app.get("/health")
def health():
    return {"status": "ok", "service": "progress-loader"}


@app.get("/program-completions")
def list_program_completions(employee_id: Optional[int] = None, with_progress: bool = False):
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

        if with_progress:
            for row in rows:
                row["progress_percent"] = _progress_percent(cur, row["id_program_completion"])

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


@app.get("/journal")
def journal(
    id_program: Optional[int] = None,
    id_department: Optional[int] = None,
    id_position: Optional[int] = None,
    employee_number: Optional[int] = None,
    name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    query = """
        SELECT pc.id_program_completion, e.employee_number, e.first_name, e.last_name,
               e.middle_name, p.name AS program_name, pc.start_date, pc.end_date,
               e.id_department, e.id_position
        FROM program_completion pc
        JOIN employee e ON e.id_employee = pc.id_employee
        JOIN program p ON p.id_program = pc.id_program
        WHERE 1 = 1
    """
    params: list = []
    if id_program is not None:
        query += " AND pc.id_program = %s"
        params.append(id_program)
    if id_department is not None:
        query += " AND e.id_department = %s"
        params.append(id_department)
    if id_position is not None:
        query += " AND e.id_position = %s"
        params.append(id_position)
    if employee_number is not None:
        query += " AND e.employee_number = %s"
        params.append(employee_number)
    if name:
        query += " AND (e.first_name ILIKE %s OR e.last_name ILIKE %s)"
        params.extend([f"%{name}%", f"%{name}%"])
    if date_from:
        query += " AND pc.start_date >= %s"
        params.append(date_from)
    if date_to:
        query += " AND pc.start_date <= %s"
        params.append(date_to)
    query += " ORDER BY pc.start_date DESC"

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        for row in rows:
            row["progress_percent"] = _progress_percent(cur, row["id_program_completion"])

    return rows


@app.get("/stats")
def dashboard_stats(
    id_program: Optional[int] = None,
    id_department: Optional[int] = None,
    id_position: Optional[int] = None,
    employee_number: Optional[int] = None,
    name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    rows = journal(
        id_program=id_program,
        id_department=id_department,
        id_position=id_position,
        employee_number=employee_number,
        name=name,
        date_from=date_from,
        date_to=date_to,
    )

    employees = {row["employee_number"] for row in rows}
    done = [row for row in rows if row["end_date"] is not None]
    in_progress = [
        row for row in rows if row["end_date"] is None and row["progress_percent"] > 0
    ]
    not_started = [
        row for row in rows if row["end_date"] is None and row["progress_percent"] == 0
    ]
    avg_percent = round(sum(row["progress_percent"] for row in rows) / len(rows)) if rows else 0

    def _entry(row):
        full_name = f"{row['last_name']} {row['first_name']} {row['middle_name'] or ''}".strip()
        return {
            "employee_number": row["employee_number"],
            "full_name": full_name,
            "progress_percent": row["progress_percent"],
        }

    ranked = sorted(rows, key=lambda row: row["progress_percent"], reverse=True)

    return {
        "employees": len(employees),
        "assigned_courses": len(rows),
        "passed": len(done),
        "in_progress": len(in_progress),
        "not_started": len(not_started),
        "average_percent": avg_percent,
        "leaders": [_entry(row) for row in ranked[:3]],
        "laggards": [_entry(row) for row in ranked[-3:][::-1]] if ranked else [],
    }
