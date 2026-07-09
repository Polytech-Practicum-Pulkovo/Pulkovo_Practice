import os

import httpx

AI_GENERATION_URL = os.getenv("AI_GENERATION_URL", "http://ai-generation:8000")


async def parse_program_file(filename: str, content: bytes) -> dict:
    """Отправляет DOCX-файл программы обучения на разбор в ai-generation.

    Возвращает {"topics": [...], "literature": [...], "hours": number}.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{AI_GENERATION_URL}/parse_program_file/",
            files={"file": (filename, content)},
        )
        response.raise_for_status()
        return response.json()


async def generate_questions(material_path: str, previous_questions: list[dict], count: int) -> list[dict]:
    """Просит ai-generation сгенерировать вопросы по материалу темы.

    previous_questions — список {"question_text", "correct_answers", "incorrect_answers"}
    для дедупликации с уже существующими в теме вопросами.
    Возвращает [{"question_text", "options", "correct_option"}, ...].
    """
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
