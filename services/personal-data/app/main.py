import os
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db import get_cursor
from app.security import generate_reset_token, hash_password, verify_password

NOTIFICATIONS_URL = os.getenv("NOTIFICATIONS_URL", "http://notifications:8000")
RESET_TOKEN_TTL_MINUTES = 60

app = FastAPI(title="Личные данные")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    employee_number: int
    password: str


class ChangePasswordRequest(BaseModel):
    employee_id: int
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    employee_number: int


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "personal-data"}


@app.post("/auth/login")
def login(payload: LoginRequest):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id_employee, e.first_name, e.last_name, e.middle_name,
                   e.employee_number, e.email, e.password_hash,
                   d.name AS department, p.name AS position
            FROM employee e
            LEFT JOIN department d ON d.id_department = e.id_department
            LEFT JOIN position p ON p.id_position = e.id_position
            WHERE e.employee_number = %s
            """,
            (payload.employee_number,),
        )
        employee = cur.fetchone()

    if not employee or not verify_password(payload.password, employee["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверный табельный номер или пароль")

    employee.pop("password_hash")
    return employee


@app.post("/auth/change-password")
def change_password(payload: ChangePasswordRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT password_hash FROM employee WHERE id_employee = %s",
            (payload.employee_id,),
        )
        employee = cur.fetchone()

    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if not verify_password(payload.old_password, employee["password_hash"]):
        raise HTTPException(status_code=401, detail="Текущий пароль указан неверно")

    new_hash = hash_password(payload.new_password)
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE employee SET password_hash = %s WHERE id_employee = %s",
            (new_hash, payload.employee_id),
        )

    return {"status": "password_changed"}


@app.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_employee, email FROM employee WHERE employee_number = %s",
            (payload.employee_number,),
        )
        employee = cur.fetchone()

    # Не раскрываем, существует ли такой email в системе.
    if employee:
        token = generate_reset_token()
        expiry = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
        with get_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE employee SET reset_token = %s, reset_token_expiry = %s "
                "WHERE id_employee = %s",
                (token, expiry, employee["id_employee"]),
            )

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(
                    f"{NOTIFICATIONS_URL}/notifications/password-reset",
                    json={"email": employee["email"], "token": token},
                )
            except httpx.HTTPError:
                pass  # доставка уведомления не должна ронять основной сценарий

    return {"status": "if_email_exists_reset_link_sent"}


@app.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_employee, reset_token_expiry FROM employee "
            "WHERE reset_token = %s",
            (payload.token,),
        )
        employee = cur.fetchone()

    if not employee or employee["reset_token_expiry"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Ссылка недействительна или устарела")

    new_hash = hash_password(payload.new_password)
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE employee SET password_hash = %s, reset_token = NULL, "
            "reset_token_expiry = NULL WHERE id_employee = %s",
            (new_hash, employee["id_employee"]),
        )

    return {"status": "password_reset"}


@app.get("/employees/{employee_id}")
def get_employee(employee_id: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT e.id_employee, e.employee_number, e.first_name, e.last_name,
                   e.middle_name, e.email, d.name AS department, p.name AS position
            FROM employee e
            LEFT JOIN department d ON d.id_department = e.id_department
            LEFT JOIN position p ON p.id_position = e.id_position
            WHERE e.id_employee = %s
            """,
            (employee_id,),
        )
        employee = cur.fetchone()

    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    return employee
