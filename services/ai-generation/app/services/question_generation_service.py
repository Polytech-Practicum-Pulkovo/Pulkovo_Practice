"""
Сервис №3: генерация вопросов теста на основе .pdf файлов (например,
нормативных актов по охране труда в аэропорту).
"""
import json
import os
import re
from app.pdf_utils import extract_text_from_pdf

# Отключаем надоедливое предупреждение urllib3 про HTTPS
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# ПАРАМЕТРЫ ЧАНКИНГА (под GigaChat-2-Pro)
# ============================================================
# GigaChat Pro имеет контекст ~128K токенов, но для качественной
# генерации вопросов лучше держать вход в районе 2000-3000 токенов.
# Для русского текста 1 токен ≈ 3.5-4 символа.
CHUNK_SIZE = 8000       # символов на один чанк (~2000 токенов)
CHUNK_OVERLAP = 800     # перекрытие между чанками (10%)
BATCH_SIZE = 5
MAX_RETRIES = 3  # Сколько раз пробуем запросить у модели, если она вернула битый JSON
MAX_BATCHES_PER_CHUNK = 2   # ← ДОБАВИТЬ
HISTORY_WINDOW = 15         # ← ДОБАВИТЬ

SYSTEM_PROMPT = (
    "Ты эксперт по охране труда в аэропорту и составитель тестовых заданий.  "
    "На основе предоставленного текста нормативного документа составь вопросы  "
    "теста с 4 вариантами ответа, из которых только один правильный.\n\n "
    "Верни ответ СТРОГО в формате JSON-массива, без пояснений, преамбул и  "
    "markdown-разметки (без ```). Формат каждого элемента:\n "
    '{ "text": "<текст вопроса>", "options": ["<вариант 1>", "<вариант 2>", '
    '"<вариант 3>", "<вариант 4>"], "correct_option": <индекс правильного варианта, '
    "начиная с 0>}\n\n "
    "Вопросы должны быть основаны только на фактах из предоставленного текста,  "
    "без домыслов."
)

BATCH_SIZE = 5
MAX_RETRIES = 3  # Сколько раз пробуем запросить у модели, если она вернула битый JSON


# ============================================================
# РАЗБИЕНИЕ ТЕКСТА НА ЧАНКИ
# ============================================================
def _split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """
    Разбивает текст на перекрывающиеся части по границам предложений.

    Логика:
      1. Берём окно размером chunk_size.
      2. Если это не последний кусок — ищем последний знак препинания
         (. ? !) в пределах окна и обрезаем по нему, чтобы не разрывать
         предложение посередине.
      3. Следующий кусок начинается с учётом overlap, чтобы сохранить
         контекст на границах.

    Args:
        text: Исходный текст (обычно из PDF).
        chunk_size: Максимальный размер чанка в символах.
        overlap: Перекрытие между соседними чанками в символах.

    Returns:
        Список строк-чанков.
    """
    if not text or not text.strip():
        return []

    # Если текст маленький — возвращаем его целиком одним чанком
    if len(text) <= chunk_size:
        return [text.strip()]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Если это не последний кусок — ищем границу предложения
        if end < text_len:
            # Ищем последний знак конца предложения в окне [start:end]
            last_boundary = -1
            for punct in ('.', '?', '!'):
                pos = text.rfind(punct, start, end)
                if pos > last_boundary:
                    last_boundary = pos

            # Если нашли границу не слишком близко к началу (хотя бы 50% от chunk_size) —
            # обрезаем по ней. Иначе режем по chunk_size как есть.
            if last_boundary > start + chunk_size // 2:
                end = last_boundary + 1  # включаем сам знак препинания

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Если дошли до конца — выходим
        if end >= text_len:
            break

        # Следующий чанк начинаем с учётом overlap
        start = end - overlap

        # Защита от зацикливания (на случай, если overlap >= chunk_size)
        if start <= (end - chunk_size):
            start = end

    return chunks


def _parse_json_response(raw_text):
    """Парсит JSON из ответа модели и пытается восстановить обрезанный массив."""
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


# ============================================================
# ВСПОМОГАТЕЛЬНАЯ: формирование промпта
# ============================================================
def _build_user_prompt(document_text, current_batch, already_generated_texts, chunk_info=None):
    """
    Формирует промпт с учётом уже сгенерированных вопросов и позиции чанка.

    Args:
        document_text: Текст текущего чанка.
        current_batch: Сколько вопросов нужно сгенерировать в этом батче.
        already_generated_texts: Список текстов уже сгенерированных вопросов (для дедупликации).
        chunk_info: Опциональная строка с информацией о позиции чанка
                    (например, "[Часть 2 из 5 документа]").
    """
    # Показываем только последние HISTORY_WINDOW вопросов, чтобы не раздувать промпт
    if already_generated_texts:
        recent = already_generated_texts[-HISTORY_WINDOW:]
        prev_block = (
            "\n\nВАЖНО: Ниже список УЖЕ СГЕНЕРИРОВАННЫХ вопросов.  "
            "НЕ ПОВТОРЯЙ их ни по смыслу, ни по формулировке.  "
            "Придумай СОВЕРШЕННО НОВЫЕ вопросы по другим фактам из текста:\n "
        )
        for i, q_text in enumerate(recent, 1):
            prev_block += f"{i}. {q_text}\n"
    else:
        prev_block = ""

    # Подсказка модели о позиции чанка
    chunk_hint = f"\n{chunk_info}\n" if chunk_info else ""

    return (
        f"Составь ровно {current_batch} новых вопросов на основе следующего текста.{chunk_hint}"
        f"{prev_block}\n\n"
        f"ТЕКСТ ДОКУМЕНТА:\n{document_text}"
    )


# ============================================================
# ЯДРО: общая логика генерации вопросов из текста
# ============================================================
async def _generate_questions_core(
    client,
    document_text: str,
    source_file: str,
    topic=None,
    num_questions=5,
    batch_size=BATCH_SIZE,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    already_generated_texts=None,
):
    """
    Общая логика генерации вопросов из уже извлечённого текста.

    Алгоритм:
      1. Разбиваем текст на перекрывающиеся чанки по ~chunk_size символов.
      2. Для каждого чанка генерируем batch_size вопросов за один вызов ИИ.
      3. Если модель вернула битый JSON — повторяем до MAX_RETRIES раз.
      4. Список уже сгенерированных вопросов передаётся в следующий батч
         для защиты от повторений.
      5. Останавливаемся, когда набрали num_questions или прошли все чанки.

    Args:
        client: Экземпляр GigaChatClient.
        document_text: Уже извлечённый текст документа.
        source_file: Имя исходного файла.
        topic: Название темы.
        num_questions: Сколько вопросов нужно сгенерировать суммарно.
        batch_size: Сколько вопросов генерировать за один вызов ИИ.
        chunk_size: Размер чанка в символах.
        chunk_overlap: Перекрытие между чанками в символах.
        already_generated_texts: Список уже существующих вопросов (от фронтенда и т.п.)
                                 — используется для дедупликации. Не мутируется.

    Returns:
        Список сгенерированных вопросов (list of dict).
    """
    if not document_text or not document_text.strip():
        raise ValueError("Пустой текст документа — нечего анализировать.")

    # Копируем входной список, чтобы не мутировать его извне
    if already_generated_texts is None:
        already_generated_texts = []
    else:
        already_generated_texts = list(already_generated_texts)

    # === ШАГ 1: РАЗБИЕНИЕ ТЕКСТА НА ЧАНКИ ===
    chunks = _split_text_into_chunks(document_text, chunk_size, chunk_overlap)
    total_chunks = len(chunks)
    print(f"📄 Текст разбит на {total_chunks} чанков "
          f"(размер ~{chunk_size} символов, overlap {chunk_overlap})")

    all_questions = []
    remaining = num_questions
    chunk_idx = 0

    # === ШАГ 2: ИТЕРАЦИЯ ПО ЧАНКАМ ===
    while remaining > 0 and chunk_idx < total_chunks:
        current_chunk = chunks[chunk_idx]
        chunk_idx += 1
        chunk_info = f"[Часть {chunk_idx} из {total_chunks} документа]"

        # Генерируем вопросы из текущего чанка батчами, пока не исчерпаем
        # remaining или максимум MAX_BATCHES_PER_CHUNK батчей на чанк
        # (чтобы не зацикливаться на одном месте и равномерно покрыть документ)
        batches_from_this_chunk = 0

        while remaining > 0 and batches_from_this_chunk < MAX_BATCHES_PER_CHUNK:
            current_batch = min(batch_size, remaining)
            print(f"  🧩 Чанк {chunk_idx}/{total_chunks}, "
                  f"батч {batches_from_this_chunk + 1}: "
                  f"генерируем {current_batch} вопросов...")

            user_prompt = _build_user_prompt(
                current_chunk, current_batch, already_generated_texts, chunk_info
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            batch_questions = None

            # === ЦИКЛ ПОВТОРНЫХ ПОПЫТОК (RETRY) ===
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    raw_response = await client.acomplete(
                        messages, temperature=0.4, max_tokens=4096
                    )
                    batch_questions = _parse_json_response(raw_response)
                    break  # Успех — выходим из цикла попыток
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"    ⚠️ Попытка {attempt}/{MAX_RETRIES} не удалась: {e}")
                    if attempt < MAX_RETRIES:
                        print(f"       Повторяем запрос к модели...")
                    else:
                        print(f"       Пропускаем батч после {MAX_RETRIES} неудачных попыток.")

            # Если модель так и не вернула валидный JSON — переходим к следующему чанку
            if batch_questions is None:
                break

            # Добавляем вопросы в общий список
            for q in batch_questions:
                all_questions.append(q)
                already_generated_texts.append(q["text"])
                remaining -= 1
                if remaining <= 0:
                    break

            batches_from_this_chunk += 1
            print(f"    ✅ Всего сгенерировано: {len(all_questions)}/{num_questions}")

    return all_questions


# ============================================================
# ОБЁРТКА 1: генерация из PDF
# ============================================================
async def generate_questions_from_pdf(
    client,
    pdf_path,
    topic=None,
    num_questions=5,
    batch_size=BATCH_SIZE,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    already_generated_texts=None,
):
    """
    Генерирует вопросы по PDF-файлу.

    Извлекает текст через pdftotext и делегирует основную работу
    в _generate_questions_core().
    """
    document_text = extract_text_from_pdf(pdf_path)
    if not document_text:
        raise ValueError(f"Не удалось извлечь текст из файла: {pdf_path}")

    return await _generate_questions_core(
        client=client,
        document_text=document_text,
        source_file=os.path.basename(pdf_path),
        topic=topic,
        num_questions=num_questions,
        batch_size=batch_size,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        already_generated_texts=already_generated_texts,
    )


# ============================================================
# ОБЁРТКА 2: генерация из готового текста (DOCX/DOC и т.п.)
# ============================================================
async def generate_questions_from_text(
    client,
    document_text: str,
    source_file: str,
    topic=None,
    num_questions=5,
    batch_size=BATCH_SIZE,
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    already_generated_texts=None,
):
    """
    Генерирует вопросы по уже извлечённому тексту (DOCX/DOC и т.п.).

    Используется, когда текст был извлечён внешним парсером
    (например, document_parser.extract_text_with_formatting).
    """
    return await _generate_questions_core(
        client=client,
        document_text=document_text,
        source_file=source_file,
        topic=topic,
        num_questions=num_questions,
        batch_size=batch_size,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        already_generated_texts=already_generated_texts,
    )