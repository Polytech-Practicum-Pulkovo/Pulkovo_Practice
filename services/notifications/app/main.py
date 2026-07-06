import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from app.db import get_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notifications")

app = FastAPI(title="Отправка уведомления")


class EmailNotification(BaseModel):
    employee_id: int
    subject: str
    body: str


class LmsNotification(BaseModel):
    employee_id: int
    message: str


class PasswordResetNotification(BaseModel):
    email: EmailStr
    token: str


def _record_notification(cur, employee_id: int) -> dict:
    cur.execute(
        "INSERT INTO notification (id_employee, date, is_viewed) "
        "VALUES (%s, %s, false) RETURNING id, id_employee, date, is_viewed",
        (employee_id, datetime.utcnow()),
    )
    return cur.fetchone()


@app.get("/health")
def health():
    return {"status": "ok", "service": "notifications"}


@app.post("/notifications/email")
def send_email(payload: EmailNotification):
    # Реальная интеграция с почтовым сервером — предмет доработки.
    logger.info("Отправка письма сотруднику %s: %s", payload.employee_id, payload.subject)
    with get_cursor(commit=True) as cur:
        record = _record_notification(cur, payload.employee_id)
    return {"status": "sent", "channel": "email", "notification": record}


@app.post("/notifications/lms")
def send_lms(payload: LmsNotification):
    logger.info("LMS-уведомление сотруднику %s: %s", payload.employee_id, payload.message)
    with get_cursor(commit=True) as cur:
        record = _record_notification(cur, payload.employee_id)
    return {"status": "sent", "channel": "lms", "notification": record}


@app.post("/notifications/password-reset")
def send_password_reset(payload: PasswordResetNotification):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_employee FROM employee WHERE email = %s",
            (payload.email,),
        )
        employee = cur.fetchone()

    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    reset_link = f"https://lms.pulkovo.local/reset-password?token={payload.token}"
    logger.info("Письмо восстановления пароля для %s: %s", payload.email, reset_link)

    with get_cursor(commit=True) as cur:
        record = _record_notification(cur, employee["id_employee"])

    return {"status": "sent", "channel": "email", "notification": record}


@app.get("/notifications")
def list_notifications(employee_id: Optional[int] = None):
    query = "SELECT id, id_employee, date, is_viewed FROM notification"
    params: tuple = ()
    if employee_id is not None:
        query += " WHERE id_employee = %s"
        params = (employee_id,)
    query += " ORDER BY date DESC"

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return rows
