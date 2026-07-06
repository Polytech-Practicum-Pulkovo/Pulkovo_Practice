"""
Сервис №1: генерация ответа на запрос пользователя, который проходит тест.

В промпт подгружается текущий вопрос теста из БД (текст вопроса и варианты
ответов), чтобы ИИ отвечал в контексте того, что именно спрашивает пользователь,
но не подсказывал правильный вариант напрямую — только помогал разобраться в теме.
"""
from app import db

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
    lines = []
    for idx, option in enumerate(options):
        letter = chr(ord("A") + idx)
        lines.append(f"{letter}) {option}")
    return "\n".join(lines)


async def answer_user_question(client, question_id, user_message, history=None):
    """
    Генерирует ответ ИИ на реплику пользователя в контексте текущего
    вопроса теста, загруженного из БД.

    :param client: экземпляр GigaChatClient
    :param question_id: id вопроса теста (из таблицы questions в БД)
    :param user_message: реплика/вопрос пользователя
    :param history: (опционально) предыдущая история диалога в формате
                     [{"role": "user"/"assistant", "content": ...}, ...]
    :return: текст ответа модели
    """
    question = db.get_question_by_id(question_id)
    if question is None:
        raise ValueError(f"Вопрос с id={question_id} не найден в БД")

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        question_text=question["text"],
        options_block=_build_options_block(question["options"]),
    )

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    return await client.acomplete(messages, temperature=0.5)
