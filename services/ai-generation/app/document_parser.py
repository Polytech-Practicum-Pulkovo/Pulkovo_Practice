from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import xml.etree.ElementTree as ET


@dataclass
class DocumentQuestion:
    """Описывает один тестовый вопрос, извлеченный из документа."""

    text: str
    options: List[str] = field(default_factory=list)
    correct_option: int | None = None
    correct_letter: str | None = None


@dataclass
class DocumentTopic:
    """Описывает тему документа вместе с количеством часов."""

    title: str
    hours: float | int | None = None


@dataclass
class DocumentAnalysis:
    """Содержит итог анализа документа: текст, темы и вопросы."""

    source_path: str
    raw_text: str = ""
    topics: List[DocumentTopic] = field(default_factory=list)
    questions: List[DocumentQuestion] = field(default_factory=list)


def analyze_document(path: str | os.PathLike) -> DocumentAnalysis:
    """Анализирует DOCX-документ без LLM и извлекает темы с вопросами."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".docx":
        raise ValueError("Поддерживаются только .docx файлы")

    paragraphs = _extract_docx_paragraphs(path)
    raw_text = "\n".join(text for text, _ in paragraphs if text)
    topics = _extract_topics(paragraphs)
    questions = _extract_questions(paragraphs)

    return DocumentAnalysis(
        source_path=str(path),
        raw_text=raw_text,
        topics=topics,
        questions=questions,
    )


def _extract_docx_paragraphs(path: Path) -> List[tuple[str, bool]]:
    """Извлекает из DOCX список абзацев и признак наличия жирного текста."""

    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
        root = ET.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: List[tuple[str, bool]] = []
        for paragraph in root.findall(".//w:p", namespace):
            parts: List[str] = []
            is_bold = False
            for run in paragraph.findall("./w:r", namespace):
                run_text = "".join(
                    text_node.text or ""
                    for text_node in run.findall("./w:t", namespace)
                )
                if run_text:
                    parts.append(run_text)
                if _run_is_bold(run, namespace):
                    is_bold = True
            text = "".join(parts).strip()
            if text:
                paragraphs.append((text, is_bold))
    return paragraphs


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _run_is_bold(run, namespace) -> bool:
    """Проверяет, содержит ли run признак жирного шрифта."""

    bold_elems = run.findall("./w:b", namespace)
    if not bold_elems:
        return False
    val = bold_elems[0].get(f"{W_NS}val")
    return val not in ("false", "0")


_TOPIC_PREFIX_PATTERN = re.compile(
    r"^\s*тема\s*(?P<number>\d+)?\s*[:\-.]?\s*(?P<body>.+?)\s*$",
    re.IGNORECASE,
)
_HOURS_PATTERN = re.compile(
    r"(?P<hours>\d+(?:[.,]\d+)?)\s*(?:академическ(?:их|ие|ий)?\s*)?(?:час(?:а|ов)?|ч\.?)(?!\w)",
    re.IGNORECASE,
)


def _normalize_hours(hours_text: str) -> float | int | None:
    """Преобразует найденное значение часов в число."""

    try:
        value = float(hours_text.replace(",", "."))
    except ValueError:
        return None
    if value.is_integer():
        return int(value)
    return value


def _extract_hours_from_text(text: str) -> float | int | None:
    """Ищет в строке значение часов и возвращает его как число."""

    matches = list(_HOURS_PATTERN.finditer(text))
    if not matches:
        return None
    return _normalize_hours(matches[-1].group("hours"))


def _parse_topic_text(text: str) -> DocumentTopic | None:
    """Выделяет название темы и часы из строки, начинающейся с 'Тема'."""

    match = _TOPIC_PREFIX_PATTERN.match(text)
    if not match:
        return None

    body = match.group("body").strip()
    hours_match = list(_HOURS_PATTERN.finditer(body))
    hours = None
    if hours_match:
        last_hours = hours_match[-1]
        hours = _normalize_hours(last_hours.group("hours"))
        body = body[:last_hours.start()].strip(" -*:;,.()")

    title = body.strip(" -*:;,.()")
    if not title:
        return None
    return DocumentTopic(title=title, hours=hours)


def _extract_topics(paragraphs: List[tuple[str, bool]]) -> List[DocumentTopic]:
    """Собирает список тем документа и подставляет часы к каждой теме."""

    topics: List[DocumentTopic] = []
    current_topic: DocumentTopic | None = None

    for text, _ in paragraphs:
        normalized = text.strip()
        if not normalized:
            continue

        parsed_topic = _parse_topic_text(normalized)
        if parsed_topic is not None:
            if current_topic is not None:
                topics.append(current_topic)
            current_topic = parsed_topic
            continue

        if current_topic is not None and current_topic.hours is None:
            hours = _extract_hours_from_text(normalized)
            if hours is not None:
                current_topic.hours = hours

    if current_topic is not None:
        topics.append(current_topic)

    return topics


def _extract_questions(paragraphs: List[tuple[str, bool]]) -> List[DocumentQuestion]:
    """Извлекает тестовые вопросы и варианты ответов из текста документа."""

    questions: List[DocumentQuestion] = []
    current_question: DocumentQuestion | None = None

    for text, is_bold in paragraphs:
        if not text:
            continue

        normalized = text.strip()
        if _looks_like_option(normalized):
            if current_question is None:
                continue
            option_text = _clean_option_text(normalized)
            current_question.options.append(option_text)
            if is_bold and current_question.correct_option is None:
                current_question.correct_option = len(current_question.options) - 1
                current_question.correct_letter = chr(ord("A") + current_question.correct_option)
            continue

        if _looks_like_question(normalized):
            if current_question is not None and current_question.options:
                questions.append(current_question)
            current_question = DocumentQuestion(text=_clean_question_text(normalized))
            continue

        if current_question is not None and current_question.options:
            questions.append(current_question)
            current_question = None

    if current_question is not None:
        if not current_question.options and _looks_like_question(current_question.text):
            questions.append(current_question)
        elif current_question.options:
            questions.append(current_question)

    return questions


def _looks_like_question(text: str) -> bool:
    """Проверяет, похожа ли строка на вопрос."""

    return text.endswith("?") or text.startswith("Вопрос") or "вопрос" in text.lower()


def _looks_like_option(text: str) -> bool:
    """Проверяет, похожа ли строка на вариант ответа."""

    return bool(re.match(r"^(?:[A-D]|[1-4])[\.)]\s*", text))


def _clean_option_text(text: str) -> str:
    """Удаляет служебную нумерацию из варианта ответа."""

    return re.sub(r"^(?:[A-D]|[1-4])[\.)]\s*", "", text).strip()


def _clean_question_text(text: str) -> str:
    """Удаляет префикс 'Вопрос:' из текста вопроса."""

    return re.sub(r"^(?:Вопрос\s*[:\-]\s*)", "", text).strip()


def _get_llm_formatted_text(path: Path) -> str:
    """Извлекает текст из DOCX и помечает жирные фрагменты для LLM."""

    if path.suffix.lower() != ".docx":
        raise ValueError("Поддерживаются только .docx файлы")

    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
        root = ET.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            parts = []
            for run in paragraph.findall("./w:r", namespace):
                run_text = "".join(
                    text_node.text or ""
                    for text_node in run.findall("./w:t", namespace)
                )
                if run_text:
                    if _run_is_bold(run, namespace):
                        parts.append(f"**{run_text}**")
                    else:
                        parts.append(run_text)
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)


LLM_SYSTEM_PROMPT = """Ты — система для извлечения тестовых вопросов из документов по охране труда.
Тебе будет предоставлен текст документа. В этом тексте правильные ответы в вопросах выделены жирным шрифтом (обернуты в **).
Твоя задача:
1. Извлечь все текстовые тестовые вопросы с вариантами ответов. Картинки и графические элементы игнорируй.
2. Для каждого вопроса определи правильный ответ, основываясь на том, какой вариант ответа был выделен жирным шрифтом (**). Убери символы ** из текста вариантов.

Верни ОТВЕТ СТРОГО в формате JSON-объекта, без markdown-разметки (без ```json), без пояснений и преамбул.
Формат JSON:
{
  "questions": [
    {
      "text": "Текст вопроса",
      "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      "correct_option": 1
    }
  ]
}
Поле correct_option — это индекс правильного ответа в массиве options (начинается с 0). Если правильный ответ не определен, укажи null."""

HOURS_SYSTEM_PROMPT = """Ты — система для извлечения общего количества часов из документа.
Тебе будет предоставлен текст документа. Найди только общее количество часов на обучение, если оно указано.

Верни ОТВЕТ СТРОГО в формате JSON-объекта, без markdown-разметки (без ```json), без пояснений и преамбул.
Формат JSON:
{
    "hours": 72
}
Если часы не найдены, укажи 0."""

LITERATURE_SYSTEM_PROMPT = """Ты — система для извлечения списка рекомендуемой литературы из документа.
Тебе будет предоставлен текст документа. Найди только список рекомендуемой литературы.
Если в тексте встречаются ГОСТ, относить их именно к литературе и включать в список литературы.

Верни ОТВЕТ СТРОГО в формате JSON-объекта, без markdown-разметки (без ```json), без пояснений и преамбул.
Формат JSON:
{
    "literature": ["Литература 1", "Литература 2"]
}
Если литература не найдена, укажи пустой список."""


def _parse_llm_json_response(raw_text: str) -> dict:
    """Достаёт JSON-объект из ответа модели, очищая от возможного markdown."""

    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


async def extract_hours_with_llm(client, doc_path: str | os.PathLike) -> float | int:
    """Извлекает общее количество часов через LLM."""

    path = Path(doc_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".docx":
        raise ValueError("Поддерживаются только .docx файлы")

    messages = [
        {"role": "system", "content": HOURS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Текст документа:\n{_get_llm_formatted_text(path)}"},
    ]

    raw_response = await client.acomplete(messages, temperature=0.1)
    print(f"🤖 LLM ответ по часам получен: {raw_response}")
    parsed = _parse_llm_json_response(raw_response)
    hours = parsed.get("hours", 0)
    if isinstance(hours, (int, float)):
        if float(hours).is_integer():
            return int(hours)
        return hours
    return 0


async def extract_literature_with_llm(client, doc_path: str | os.PathLike) -> List[str]:
    """Извлекает список рекомендуемой литературы через LLM."""

    path = Path(doc_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".docx":
        raise ValueError("Поддерживаются только .docx файлы")

    messages = [
        {"role": "system", "content": LITERATURE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Текст документа:\n{_get_llm_formatted_text(path)}"},
    ]

    raw_response = await client.acomplete(messages, temperature=0.1)
    print(f"🤖 LLM ответ по литературе получен: {raw_response}")
    parsed = _parse_llm_json_response(raw_response)
    literature = parsed.get("literature", [])
    if not isinstance(literature, list):
        return []
    return [str(item).strip() for item in literature if str(item).strip()]


async def analyze_document_with_llm(client, path: str | os.PathLike) -> DocumentAnalysis:
    """Анализирует DOCX через LLM: темы берет из текста, вопросы — из модели."""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".docx":
        raise ValueError("Поддерживаются только .docx файлы")

    llm_text = _get_llm_formatted_text(path)
    raw_paragraphs = _extract_docx_paragraphs(path)
    raw_text = "\n".join(text for text, _ in raw_paragraphs if text)
    topics = _extract_topics(raw_paragraphs)

    messages = [
        {"role": "system", "content": LLM_SYSTEM_PROMPT},
        {"role": "user", "content": f"Текст документа:\n{llm_text}"},
    ]

    raw_response = await client.acomplete(messages, temperature=0.1)
    print(f"🤖 LLM ответ по вопросам получен: {raw_response}")
    parsed = _parse_llm_json_response(raw_response)

    questions = []
    for q in parsed.get("questions", []):
        text = q.get("text", "").strip()
        options = [opt.strip().replace("**", "") for opt in q.get("options", [])]
        correct_option = q.get("correct_option")

        if text and options:
            if correct_option is not None and (
                not isinstance(correct_option, int) or correct_option < 0 or correct_option >= len(options)
            ):
                correct_option = None

            questions.append(
                DocumentQuestion(
                    text=text,
                    options=options,
                    correct_option=correct_option,
                    correct_letter=chr(ord("A") + correct_option) if correct_option is not None else None,
                )
            )

    return DocumentAnalysis(
        source_path=str(path),
        raw_text=raw_text,
        topics=topics,
        questions=questions,
    )


def extract_program_structure(doc_path: str | os.PathLike) -> dict:
    """Ручное извлечение структуры программы обучения из DOCX/DOC."""

    from docx import Document
    doc = Document(doc_path)
    topics = []
    literature = []
    hours = 0
    current_section = None
    
    # 1. Rule-based парсинг параграфов
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Ищем темы
        if "тема" in text.lower() or para.style.name.startswith("Heading"):
            current_section = "topics"
            topic_name = re.sub(r"^тема\s*\d+[:\.\s]*", "", text, flags=re.IGNORECASE).strip()
            if topic_name and not re.search(r"\bгост\b", topic_name, re.IGNORECASE):
                topics.append(topic_name)
            continue

        # Ищем раздел литературы
        if "литератур" in text.lower():
            current_section = "literature"
            continue

        # Собираем литературу (поддерживаем нумерованные списки и буллиты)
        if current_section == "literature":
            match = re.match(r"^\d+[\.\)]\s*(.*)", text)
            if match:
                literature.append(match.group(1).strip())
                continue
            if text.startswith(("•", "-", "—")):
                literature.append(text.lstrip("•-— ").strip())
                continue
            if re.search(r"\bгост\b", text, re.IGNORECASE):
                literature.append(text.strip())
                continue
            # Строка не похожа на пункт литературы — раздел литературы закончился,
            # проверяем эту же строку на часы ниже.
            current_section = None

        # Ищем часы в тексте
        if "час" in text.lower():
            match = re.search(r"(\d+(?:[.,]\d+)?)\s*час", text, re.IGNORECASE)
            if match:
                hours = float(match.group(1).replace(",", "."))
                if hours.is_integer():
                    hours = int(hours)

    # 2. Поиск часов в таблицах (если в параграфах не нашли)
    if hours == 0:
        for table in doc.tables:
            for row in table.rows:
                row_text = " ".join(cell.text.strip() for cell in row.cells)
                # Ищем строку с "Итого" или "Всего"
                if "итого" in row_text.lower() or "всего" in row_text.lower():
                    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:час|ч)", row_text, re.IGNORECASE)
                    if match:
                        hours = float(match.group(1).replace(",", "."))
                        if hours.is_integer():
                            hours = int(hours)
                        break
            if hours > 0:
                break

    return {
        "topics": topics,
        "literature": literature,
        "hours": hours,
    }

def extract_text_with_formatting(doc_path: str) -> str:
    """
    Публичная обёртка над _get_llm_formatted_text.
    Извлекает текст из DOCX и помечает жирные фрагменты для LLM.
    
    Args:
        doc_path: Путь к DOCX файлу (str или Path).
    
    Returns:
        Текст документа, где жирные фрагменты обёрнуты в **...**.
    """
    return _get_llm_formatted_text(Path(doc_path))