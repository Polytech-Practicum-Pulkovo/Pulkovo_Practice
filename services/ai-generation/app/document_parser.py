from __future__ import annotations
import os
import re
import subprocess
import tempfile
import zipfile
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import xml.etree.ElementTree as ET
import shutil


@dataclass
class DocumentQuestion:
    text: str
    options: List[str] = field(default_factory=list)
    correct_option: int | None = None
    correct_letter: str | None = None


@dataclass
class DocumentAnalysis:
    source_path: str
    raw_text: str = ""
    topics: List[str] = field(default_factory=list)
    questions: List[DocumentQuestion] = field(default_factory=list)


def analyze_document(path: str | os.PathLike) -> DocumentAnalysis:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        paragraphs = _extract_docx_paragraphs(path)
    elif suffix == ".doc":
        paragraphs = _extract_doc_paragraphs(path)
    else:
        raise ValueError("Поддерживаются только .doc и .docx файлы")

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
    bold_elems = run.findall("./w:b", namespace)
    if not bold_elems:
        return False
    val = bold_elems[0].get(f"{W_NS}val")
    return val not in ("false", "0")


def _convert_with_libreoffice(path: Path, target_ext: str) -> Path | None:
    if not _has_command("soffice"):
        return None
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", target_ext,
             "--outdir", tmp_dir, str(path)],
            capture_output=True, check=False, timeout=60,
        )
        converted = Path(tmp_dir) / f"{path.stem}.{target_ext}"
        if not converted.exists():
            return None
        dest = Path(tempfile.gettempdir()) / converted.name
        shutil.copy(converted, dest)
        return dest


def _extract_doc_paragraphs(path: Path) -> List[tuple[str, bool]]:
    converted = _convert_with_libreoffice(path, "docx")
    if converted:
        try:
            return _extract_docx_paragraphs(converted)
        finally:
            converted.unlink(missing_ok=True)
    return []


def _has_command(command: str) -> bool:
    try:
        subprocess.run([command, "--help"], capture_output=True, check=False)
    except FileNotFoundError:
        return False
    return True


_TOPIC_PATTERN = re.compile(r"^\s*тема\s*\d*\s*[:\-.]?\s*(.+)$", re.IGNORECASE)


def _extract_topics(paragraphs: List[tuple[str, bool]]) -> List[str]:
    topics: List[str] = []
    for text, _ in paragraphs:
        match = _TOPIC_PATTERN.match(text)
        if not match:
            continue
        title = match.group(1).strip(" -*:")
        if title and title not in topics:
            topics.append(title)
    return topics


def _extract_questions(paragraphs: List[tuple[str, bool]]) -> List[DocumentQuestion]:
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
    return text.endswith("?") or text.startswith("Вопрос") or "вопрос" in text.lower()


def _looks_like_option(text: str) -> bool:
    return bool(re.match(r"^(?:[A-D]|[1-4])[\.)]\s*", text))


def _clean_option_text(text: str) -> str:
    return re.sub(r"^(?:[A-D]|[1-4])[\.)]\s*", "", text).strip()


def _clean_question_text(text: str) -> str:
    return re.sub(r"^(?:Вопрос\s*[:\-]\s*)", "", text).strip()



# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ LLM (GigaChat) ====================

def _get_llm_formatted_text(path: Path) -> str:
    """Извлекает текст из DOCX/DOC, оборачивая жирные фрагменты в ** для LLM."""
    if path.suffix.lower() == ".doc":
        converted = _convert_with_libreoffice(path, "docx")
        if converted:
            try:
                return _get_llm_formatted_text(converted)
            finally:
                converted.unlink(missing_ok=True)
        return ""

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
                    # Если ран жирный, оборачиваем его в **
                    if _run_is_bold(run, namespace):
                        parts.append(f"**{run_text}**")
                    else:
                        parts.append(run_text)
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)


LLM_SYSTEM_PROMPT = """Ты — система для извлечения тем и тестовых вопросов из документов по охране труда.
Тебе будет предоставлен текст документа. В этом тексте правильные ответы в вопросах выделены жирным шрифтом (обернуты в **).
Твоя задача:
1. Извлечь все темы, встречающиеся в документе. Тема должна быть осмысленной, содержать слова и быть непустой (отсеивай темы, состоящие только из цифр, точек или символов).
2. Извлечь все текстовые тестовые вопросы с вариантами ответов. Картинки и графические элементы игнорируй.
3. Для каждого вопроса определи правильный ответ, основываясь на том, какой вариант ответа был выделен жирным шрифтом (**). Убери символы ** из текста вариантов.

Верни ОТВЕТ СТРОГО в формате JSON-объекта, без markdown-разметки (без ```json), без пояснений и преамбул.
Формат JSON:
{
  "topics": [
    "Название темы 1",
    "Название темы 2"
  ],
  "questions": [
    {
      "text": "Текст вопроса",
      "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      "correct_option": 1
    }
  ]
}
Поле correct_option — это индекс правильного ответа в массиве options (начинается с 0). Если правильный ответ не определен, укажи null."""


def _parse_llm_json_response(raw_text: str) -> dict:
    """Достаёт JSON-объект из ответа модели, очищая от возможного markdown."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


async def analyze_document_with_llm(client, path: str | os.PathLike) -> DocumentAnalysis:
    """
    Анализирует документ с помощью LLM (GigaChat), извлекая темы и вопросы.
    Правильные ответы в вопросах должны быть выделены жирным шрифтом в исходном документе.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix not in (".doc", ".docx"):
        raise ValueError("Поддерживаются только .doc и .docx файлы")

    # Получаем текст с разметкой жирного шрифта для LLM
    llm_text = _get_llm_formatted_text(path)

    # Получаем сырой текст для метаданных
    if suffix == ".docx":
        raw_paragraphs = _extract_docx_paragraphs(path)
    else:
        raw_paragraphs = _extract_doc_paragraphs(path)
    raw_text = "\n".join(text for text, _ in raw_paragraphs if text)

    messages = [
        {"role": "system", "content": LLM_SYSTEM_PROMPT},
        {"role": "user", "content": f"Текст документа:\n{llm_text}"}
    ]

    raw_response = await client.acomplete(messages, temperature=0.1)
    parsed = _parse_llm_json_response(raw_response)

    # Фильтруем темы: оставляем только непустые, содержащие буквы (кириллицу или латиницу)
    topics = [
        t.strip() for t in parsed.get("topics", [])
        if t and re.search(r"[а-яa-z]", t, re.IGNORECASE)
    ]

    questions = []
    for q in parsed.get("questions", []):
        text = q.get("text", "").strip()
        # Убираем случайные ** из вариантов, если LLM их оставила
        options = [opt.strip().replace("**", "") for opt in q.get("options", [])]
        correct_option = q.get("correct_option")

        if text and options:
            # Проверяем валидность индекса
            if correct_option is not None and (
                    not isinstance(correct_option, int) or correct_option < 0 or correct_option >= len(options)):
                correct_option = None

            questions.append(DocumentQuestion(
                text=text,
                options=options,
                correct_option=correct_option,
                correct_letter=chr(ord("A") + correct_option) if correct_option is not None else None
            ))

    return DocumentAnalysis(
        source_path=str(path),
        raw_text=raw_text,
        topics=topics,
        questions=questions
    )