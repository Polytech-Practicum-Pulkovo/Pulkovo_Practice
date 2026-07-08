from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.catalogs import list_catalog_files, read_catalog_file
from app.db import get_all_acts, get_questions_for_topic, get_topic_by_id
from app.gigachat_client import GigaChatClient
from app.services.answer_service import answer_user_question
from app.services.topic_distribution_service import distribute_acts_to_topics

app = FastAPI(title="ИИ Генерация")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswerRequest(BaseModel):
    question: str
    topic_id: int | None = None
    catalog_file: str | None = None


class TopicDistributionRequest(BaseModel):
    program_name: str
    topics: list[str]


class QuestionsRequest(BaseModel):
    topic_name: str
    count: int = 5


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-generation"}


@app.get("/catalogs")
def get_catalogs():
    return {"files": list_catalog_files()}


@app.post("/generate/answer")
async def generate_answer(payload: AnswerRequest):
    context = ""
    if payload.catalog_file:
        try:
            context = read_catalog_file(payload.catalog_file)
        except FileNotFoundError:
            context = ""

    client = GigaChatClient()
    if payload.topic_id is not None:
        topic = get_topic_by_id(payload.topic_id)
        if topic is None:
            return {"answer": "Тема не найдена"}
        prompt = (
            f"Тема обучения: {topic['name']}\n\n"
            f"Вопрос пользователя: {payload.question}\n\n"
            f"Контекст:\n{context}"
        ).strip()
    else:
        prompt = f"{payload.question}\n\nКонтекст:\n{context}".strip()
    answer = await client.acomplete([{"role": "user", "content": prompt}])
    return {"answer": answer}


@app.post("/generate/topic-distribution")
async def generate_topic_distribution(payload: TopicDistributionRequest):
    client = GigaChatClient()
    topics = [
        {"id": index + 1, "name": topic, "description": topic}
        for index, topic in enumerate(payload.topics)
    ]
    acts = get_all_acts()
    distribution = await distribute_acts_to_topics(
        client,
        persist=True,
        topics=topics,
        acts=acts,
    )
    return {"distribution": distribution}


@app.post("/generate/questions")
async def generate_questions(payload: QuestionsRequest):
    questions = get_questions_for_topic(payload.topic_name, limit=payload.count)
    return {"questions": questions}
