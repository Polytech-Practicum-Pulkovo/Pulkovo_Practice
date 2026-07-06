import os

import httpx

AI_GENERATION_URL = os.getenv("AI_GENERATION_URL", "http://ai-generation:8000")


async def generate_topic_distribution(program_name: str, topics: list[str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{AI_GENERATION_URL}/generate/topic-distribution",
            json={"program_name": program_name, "topics": topics},
        )
        response.raise_for_status()
        return response.json()["distribution"]


async def generate_questions(topic_name: str, count: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{AI_GENERATION_URL}/generate/questions",
            json={"topic_name": topic_name, "count": count},
        )
        response.raise_for_status()
        return response.json()["questions"]
