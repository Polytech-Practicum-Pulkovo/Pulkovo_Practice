"""
Сервис №1: генерация ответа на запрос пользователя, который проходит тест.

В промпт подгружается текущий вопрос теста (текст вопроса и варианты ответов),
чтобы ИИ отвечал в контексте того, что именно спрашивает пользователь, но не
подсказывал правильный вариант напрямую — только помогал разобраться в теме.
"""
from app.pdf_utils import extract_text_from_pdf

SOURCE_CONTEXT_LIMIT = 12000

SYSTEM_PROMPT_TEMPLATE = (
    "Ты эксперт по охране труда в аэропорту, который помогает пользователю "
    "разобраться в вопросе теста, который он сейчас проходит.\n\n"
    "Текущий вопрос теста:\n\"{question_text}\"\n"
    "Варианты ответа:\n{options_block}\n\n"
    "Правила:\n"
    "1. Отвечай только на вопросы, связанные с охраной труда, безопасностью "
    "полётов, инструкциями, рисками и нормативами в аэропортовой среде.\n"
    "2. НИКОГДА не называй прямо, какой вариант ответа правильный, и не пиши "
    "его номер/букву — только поясняй суть темы, чтобы пользователь мог "
    "рассуждать самостоятельно.\n"
    "3. Если вопрос пользователя не относится к теме — кратко откажи: "
    "'Вопрос не относится к области охраны труда в аэропорту'.\n"
    "4. Отвечай строго в 2–3 предложениях, без списков и форматирования."
)


def _build_options_block(options):
    """Формирует текстовый блок с вариантами ответа для промпта."""

    lines = []
    for idx, option in enumerate(options):
        letter = chr(ord("A") + idx)
        lines.append(f"{letter}) {option}")
    return "\n".join(lines)


async def answer_user_question(client, question, user_message, history=None):
    """Отвечает пользователю в контексте текущего тестового вопроса."""

    if question is None:
        raise ValueError("Текущий вопрос не передан")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        question_text=question["text"],
        options_block=_build_options_block(question["options"]),
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        user_count = sum(1 for msg in history if msg["role"] == "user")
        if user_count > 5:
            user_indices = [i for i, msg in enumerate(history) if msg["role"] == "user"]
            start_index = user_indices[-5]
            messages.extend(history[start_index:])
        else:
            messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    return await client.acomplete(messages, temperature=0.5)


async def generate_chat_answer(client, request_text: str, chat_history: list = None, material_path: str | None = None):
    """
    Генерирует ответ чата.
    
    Args:
        client: GigaChatClient
        request_text: Текущий запрос пользователя
        chat_history: История в формате [{"role": ..., "content": ...}]
        material_path: Путь к PDF, по которому нужно отвечать в контексте документа.
    """
    messages = []
    if chat_history:
        messages.extend(chat_history)

    if material_path:
        document_text = extract_text_from_pdf(material_path)
        if document_text:
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": (
                        "Отвечай на вопросы с опорой на текст этого PDF-документа. "
                        "Если ответ есть в документе, используй его как основной источник.\n\n"
                        f"ТЕКСТ PDF:\n{document_text[:SOURCE_CONTEXT_LIMIT]}"
                    ),
                },
            )

    messages.append({"role": "user", "content": request_text})
    
    return await client.acomplete(messages, temperature=0.5)
