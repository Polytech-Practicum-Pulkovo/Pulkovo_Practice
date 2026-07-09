import os

import httpx

NOTIFICATIONS_URL = os.getenv("NOTIFICATIONS_URL", "http://notifications:8000")
AI_GENERATION_URL = os.getenv("AI_GENERATION_URL", "http://ai-generation:8000")


async def notify_lms(employee_id: int, message: str) -> None:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(
                f"{NOTIFICATIONS_URL}/notifications/lms",
                json={"employee_id": employee_id, "message": message},
            )
        except httpx.HTTPError:
            pass


async def generate_chat_answer(
    request_text: str,
    chat_history: list[dict],
    material_path: str | None = None,
) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{AI_GENERATION_URL}/generate_chat_answer/",
            json={
                "request_text": request_text,
                "material_path": material_path,
                "chat_history": chat_history,
            },
        )
        response.raise_for_status()
        return response.json()["answer"]


async def generate_questions(material_path: str, previous_questions: list[dict], count: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{AI_GENERATION_URL}/generate_questions/",
            json={
                "material_path": material_path,
                "previous_questions": previous_questions,
                "questions_amt": count,
            },
        )
        response.raise_for_status()
        return response.json()["questions"]
