"""
FastAPI-приложение: HTTP-слой для AI-сервисов.
Реализует контракт: /parse_program_file/, /generate_questions/, /generate_chat_answer/
"""
import asyncio
import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.gigachat_client import GigaChatClient
from app.services import answer_service
from app.services import question_generation_service
from app.document_parser import (
    extract_program_structure,
    extract_hours_with_llm,
    extract_literature_with_llm,
    extract_text_with_formatting,
)

app = FastAPI(title="AI Generation Service")

# Директория для временного хранения загруженных файлов
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/ai-uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# Pydantic-модели запросов (контракт с фронтендом)
# ============================================================
class PreviousQuestion(BaseModel):
    """Ранее сгенерированный вопрос — передаётся для дедупликации."""
    question_text: str
    correct_answers: List[str]
    incorrect_answers: List[str]


class GenerateQuestionsRequest(BaseModel):
    """Запрос на генерацию вопросов."""
    material_path: str
    previous_questions: List[PreviousQuestion] = []
    questions_amt: int = 5


class ChatMessage(BaseModel):
    """Сообщение в истории чата (OpenAI-формат)."""
    role: str  # "user" | "assistant" | "system"
    content: str


class GenerateChatAnswer(BaseModel):
    """Запрос на генерацию ответа чата."""
    request_text: str
    material_path: Optional[str] = None
    chat_history: List[ChatMessage] = []


# ============================================================
# Эндпоинт 1: парсинг программы обучения (DOCX/DOC)
# ============================================================
@app.post("/parse_program_file/")
async def parse_program_file(file: UploadFile = File(...)):
    """
    Принимает DOCX файл программы обучения.
    Извлекает: темы, литературу, количество часов.
    """
    print(f"📄 Получен файл: {file.filename}")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix != ".docx":
        raise HTTPException(
            status_code=400,
            detail="parse_program_file поддерживает только .docx. .doc нужно сначала сохранить/конвертировать в .docx.",
        )
    
    # 1. Сохраняем загруженный файл во временную директорию
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=UPLOAD_DIR) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 2. Ручной парсинг структуры программы
        structure = extract_program_structure(tmp_path)

        # 3. Отдельно добираем часы и литературу через LLM только если ручного парсинга не хватило
        client = GigaChatClient()
        llm_tasks = []
        if not structure["hours"]:
            print("🤖 Ручной парсинг не нашел часы, обращаемся к LLM...")
            llm_tasks.append(("hours", extract_hours_with_llm(client, tmp_path)))
        if not structure["literature"]:
            print("🤖 Ручной парсинг не нашел литературу, обращаемся к LLM...")
            llm_tasks.append(("literature", extract_literature_with_llm(client, tmp_path)))

        if llm_tasks:
            results = await asyncio.gather(*(task for _, task in llm_tasks))
            for (key, _), value in zip(llm_tasks, results):
                structure[key] = value

        print(f"✅ Извлечено тем: {len(structure['topics'])}")
        return {
            "topics": structure["topics"],
            "literature": structure.get("literature", []),
            "hours": structure.get("hours", 0),
        }
    except Exception as e:
        print(f"❌ Ошибка при парсинге файла: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 4. Чистим временный файл
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# Эндпоинт 2: генерация вопросов
# ============================================================
@app.post("/generate_questions/")
async def generate_questions(gqr: GenerateQuestionsRequest):
    """
    Генерирует вопросы по учебному материалу.
    Учитывает уже существующие вопросы (previous_questions) для дедупликации.
    """
    print(f"📝 Получен запрос на генерацию {gqr.questions_amt} вопросов")
    print(f"   Путь к материалу: {gqr.material_path}")
    print(f"   Предыдущих вопросов: {len(gqr.previous_questions)}")
    
    material_path = gqr.material_path

    # Проверка, что файл существует
    if not os.path.exists(material_path):
        raise HTTPException(status_code=404, detail=f"Файл не найден: {material_path}")

    # Преобразуем previous_questions в формат, понятный сервису
    already_generated = [pq.question_text for pq in gqr.previous_questions]

    client = GigaChatClient()

    # Определяем тип файла и вызываем соответствующую логику
    ext = os.path.splitext(material_path)[1].lower()
    if ext not in (".pdf", ".pptx", ".docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат материала: {ext}. Поддерживаются .pdf, .pptx, .docx.",
        )

    try:
        if ext == ".pdf":
            questions = await question_generation_service.generate_questions_from_pdf(
                client=client,
                pdf_path=material_path,
                topic=None,
                num_questions=gqr.questions_amt,
                already_generated_texts=already_generated,
            )
        elif ext == ".pptx":
            from app.pptx_utils import extract_text_from_pptx

            document_text = extract_text_from_pptx(material_path)
            questions = await question_generation_service.generate_questions_from_text(
                client=client,
                document_text=document_text,
                source_file=os.path.basename(material_path),
                num_questions=gqr.questions_amt,
                already_generated_texts=already_generated,
            )
        elif ext == ".docx":
            formatted_text = extract_text_with_formatting(material_path)
            questions = await question_generation_service.generate_questions_from_text(
                client=client,
                document_text=formatted_text,
                source_file=os.path.basename(material_path),
                num_questions=gqr.questions_amt,
                already_generated_texts=already_generated,
            )

        print(f"✅ Сгенерировано вопросов: {len(questions)}")
        
        # Приводим к формату ответа фронтенда
        return {
            "questions": [
                {
                    "question_text": q["text"],
                    "options": q["options"],
                    "correct_option": q["correct_option"],
                }
                for q in questions
            ]
        }
    except Exception as e:
        print(f"❌ Ошибка при генерации вопросов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Эндпоинт 3: ответ чата
# ============================================================
@app.post("/generate_chat_answer/")
async def generate_chat_answer(gca: GenerateChatAnswer):
    """
    Генерирует ответ чата с учётом истории диалога.
    """
    print(f"💬 Получен запрос чата: {gca.request_text}")
    print(f"   PDF-материал: {gca.material_path}")
    print(f"   История: {len(gca.chat_history)} сообщений")
    
    client = GigaChatClient()

    try:
        answer = await answer_service.generate_chat_answer(
            client=client,
            request_text=gca.request_text,
            chat_history=[{"role": msg.role, "content": msg.content} for msg in gca.chat_history],
            material_path=gca.material_path,
        )
        print(f"✅ Ответ получен (длина: {len(answer)} символов)")
        return {"answer": answer}
    except Exception as e:
        print(f"❌ Ошибка при генерации ответа чата: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Health-check
# ============================================================
@app.get("/health")
async def health():
    return {"status": "ok"}


# ============================================================
# Список всех маршрутов (для отладки)
# ============================================================
@app.get("/routes")
async def list_routes():
    """Возвращает список всех зарегистрированных маршрутов."""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": routes}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)