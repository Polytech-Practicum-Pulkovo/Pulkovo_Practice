from fastapi import FastAPI
from pydantic import BaseModel

from app import gigachat_client
from app.catalogs import list_catalog_files, read_catalog_file

app = FastAPI(title="ИИ Генерация")


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
def generate_answer(payload: AnswerRequest):
    context = ""
    if payload.catalog_file:
        try:
            context = read_catalog_file(payload.catalog_file)
        except FileNotFoundError:
            context = ""

    answer = gigachat_client.generate_answer(payload.question, context)
    return {"answer": answer}


@app.post("/generate/topic-distribution")
def generate_topic_distribution(payload: TopicDistributionRequest):
    distribution = gigachat_client.generate_topic_distribution(
        payload.program_name, payload.topics
    )
    return {"distribution": distribution}


@app.post("/generate/questions")
def generate_questions(payload: QuestionsRequest):
    questions = gigachat_client.generate_questions(payload.topic_name, payload.count)
    return {"questions": questions}
