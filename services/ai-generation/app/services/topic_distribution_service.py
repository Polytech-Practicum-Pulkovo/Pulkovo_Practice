"""
Сервис №2: распределение теоретических материалов (актов) по заранее
заданным темам.

Акты сейчас — заглушка: текстовые теоретические материалы, хранящиеся
в БД (в реальности могут быть выдержками из нормативных документов).
Темы также заранее заданы (таблица topics).

Модель получает список тем и список актов и должна вернуть строгий JSON
с распределением: для каждого акта — id наиболее подходящей темы,
уверенность и краткое обоснование.
"""
import json
import re

from app import db

SYSTEM_PROMPT = (
    "Ты эксперт по охране труда в аэропорту. Тебе дан список заранее заданных "
    "тем и список теоретических материалов (актов). Для каждого акта определи "
    "наиболее подходящую тему из списка.\n\n"
    "Верни ОТВЕТ СТРОГО в формате JSON-массива, без каких-либо пояснений, "
    "преамбул или markdown-разметки (без ```). Формат каждого элемента:\n"
    '{"act_id": <id акта>, "topic_id": <id темы>, "confidence": <число от 0 до 1>, '
    '"reasoning": "<краткое обоснование в одном предложении>"}\n\n'
    "Если ни одна тема не подходит достаточно хорошо, всё равно выбери "
    "ближайшую по смыслу и укажи меньшую confidence."
)


def _build_user_prompt(topics, acts):
    topics_block = "\n".join(
        f"- id={t['id']}: {t['name']} — {t['description']}" for t in topics
    )
    acts_block = "\n\n".join(
        f"Акт id={a['id']}, заголовок: \"{a['title']}\"\nТекст: {a['text']}"
        for a in acts
    )
    return (
        f"Темы:\n{topics_block}\n\n"
        f"Акты для распределения:\n{acts_block}"
    )


def _parse_json_response(raw_text):
    """Достаёт JSON-массив из ответа модели, даже если она обернула его в текст/markdown."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    return json.loads(cleaned)


async def distribute_acts_to_topics(client, persist=True, topics=None, acts=None):
    """
    Запрашивает у модели распределение актов по темам и (опционально)
    сохраняет результат в БД (таблица act_topic_map).

    :param client: экземпляр GigaChatClient
    :param persist: сохранять ли результат в БД
    :return: список словарей вида
             {"act_id":.., "topic_id":.., "confidence":.., "reasoning":..}
    """
    if topics is None:
        topics = db.get_all_topics()
    if acts is None:
        acts = db.get_all_acts()

    if not topics or not acts:
        raise ValueError("В БД должны быть заполнены и темы, и акты")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(topics, acts)},
    ]

    raw_response = await client.acomplete(messages, temperature=0.2)
    assignments = _parse_json_response(raw_response)

    if persist:
        for item in assignments:
            db.save_act_topic_assignment(
                act_id=item["act_id"],
                topic_id=item["topic_id"],
                confidence=item.get("confidence"),
                reasoning=item.get("reasoning"),
            )

    return assignments
