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


async def ask_ai_assistant(question: str, topic_id: int | None, catalog_file: str | None = None) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{AI_GENERATION_URL}/generate/answer",
            json={"question": question, "topic_id": topic_id, "catalog_file": catalog_file},
        )
        response.raise_for_status()
        return response.json()["answer"]
