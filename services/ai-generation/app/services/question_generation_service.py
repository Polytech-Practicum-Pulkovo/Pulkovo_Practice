"""
Сервис №3: генерация вопросов теста на основе .pdf файлов (например,
нормативных актов по охране труда в аэропорту).
"""
import json
import os
import re

from app import db
from app.pdf_utils import extract_text_from_pdf

# Отключаем надоедливое предупреждение urllib3 про HTTPS
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SYSTEM_PROMPT = (
    "Ты эксперт по охране труда в аэропорту и составитель тестовых заданий. "
    "На основе предоставленного текста нормативного документа составь вопросы "
    "теста с 4 вариантами ответа, из которых только один правильный.\n\n"
    "Верни ответ СТРОГО в формате JSON-массива, без пояснений, преамбул и "
    "markdown-разметки (без ```). Формат каждого элемента:\n"
    '{"text": "<текст вопроса>", "options": ["<вариант 1>", "<вариант 2>", '
    '"<вариант 3>", "<вариант 4>"], "correct_option": <индекс правильного варианта, '
    "начиная с 0>}\n\n"
    "Вопросы должны быть основаны только на фактах из предоставленного текста, "
    "без домыслов."
)

BATCH_SIZE = 5
MAX_RETRIES = 3  # Сколько раз пробуем запросить у модели, если она вернула битый JSON


def _parse_json_response(raw_text):
    """
    Парсит JSON из ответа модели.
    Пытается очистить от markdown-обёрток и «починить» обрезанный JSON.
    """
    cleaned = raw_text.strip()

    # Удаляем markdown-обёртки ```json ... ```
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    # Ищем массив [...]
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    else:
        # Если массив не закрыт моделью, берем всё, что начинается с [
        match = re.search(r"\[.*", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)

    # Первая попытка распарсить как есть
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass  # JSON битый, пробуем чинить ниже

    # === ПОЧИНКА ОБРЕЗАННОГО JSON ===
    # Ищем последнюю закрывающую скобку объекта }
    last_brace = cleaned.rfind('}')
    if last_brace != -1:
        # Отрезаем "хвост", который модель не успела дописать
        truncated = cleaned[:last_brace + 1]

        # Закрываем массив
        if not truncated.endswith(']'):
            truncated = truncated.rstrip(',') + ']'

        try:
            return json.loads(truncated)
        except json.JSONDecodeError:
            pass

    # Если вообще ничего не вышло, кидаем ошибку с сырым текстом для отладки
    raise ValueError(f"Модель вернула невалидный JSON. Сырой ответ:\n{raw_text[:500]}...")


def _build_user_prompt(document_text, current_batch, already_generated_texts):
    """Формирует промпт с учётом уже сгенерированных вопросов."""
    if already_generated_texts:
        prev_block = (
            "\n\nВАЖНО: Ниже список УЖЕ СГЕНЕРИРОВАННЫХ вопросов. "
            "НЕ ПОВТОРЯЙ их ни по смыслу, ни по формулировке. "
            "Придумай СОВЕРШЕННО НОВЫЕ вопросы по другим фактам из текста:\n"
        )
        for i, q_text in enumerate(already_generated_texts, 1):
            prev_block += f"{i}. {q_text}\n"
    else:
        prev_block = ""

    return (
        f"Составь ровно {current_batch} новых вопросов на основе следующего текста."
        f"{prev_block}\n\n"
        f"ТЕКСТ ДОКУМЕНТА:\n{document_text}"
    )


async def generate_questions_from_pdf(
        client,
        pdf_path,
        topic=None,
        num_questions=5,
        persist=True,
        batch_size=BATCH_SIZE,
):
    document_text = extract_text_from_pdf(pdf_path)
    if not document_text:
        raise ValueError(f"Не удалось извлечь текст из файла: {pdf_path}")

    all_questions = []
    already_generated_texts = []

    remaining = num_questions
    iteration = 0

    print(f"Начинаем генерацию {num_questions} вопросов батчами по {batch_size}...")

    while remaining > 0:
        current_batch = min(batch_size, remaining)
        iteration += 1

        print(f"  Батч {iteration}: генерируем {current_batch} вопросов...")

        user_prompt = _build_user_prompt(
            document_text, current_batch, already_generated_texts
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        batch_questions = None

        # === ЦИКЛ ПОВТОРНЫХ ПОПЫТОК (RETRY) ===
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw_response = await client.acomplete(messages, temperature=0.4, max_tokens=4096)
                batch_questions = _parse_json_response(raw_response)
                break  # Успех, выходим из цикла попыток

            except (json.JSONDecodeError, ValueError) as e:
                print(f"  ⚠️ Попытка {attempt}/{MAX_RETRIES} не удалась: {e}")
                if attempt < MAX_RETRIES:
                    print(f"     Повторяем запрос к модели...")
                else:
                    print(f"    Пропускаем батч после {MAX_RETRIES} неудачных попыток.")

        # Если модель всё равно вернула битый JSON, batch_questions останется None
        if batch_questions is None:
            remaining -= current_batch
            continue

        # Добавляем вопросы в общий список
        for q in batch_questions:
            all_questions.append(q)
            already_generated_texts.append(q["text"])

        remaining -= current_batch
        print(f"  Всего сгенерировано: {len(all_questions)}/{num_questions}")

    # Сохраняем в БД
    source_file = os.path.basename(pdf_path)
    if persist:
        for q in all_questions:
            db.save_generated_question(
                source_file=source_file,
                topic=topic,
                text=q["text"],
                options=q["options"],
                correct_option=q["correct_option"],
            )
        print(f"Сохранено в БД: {len(all_questions)} вопросов")

    return all_questions