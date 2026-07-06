"""Заглушка клиента GigaChat API.

Интеграция с реальным GigaChat API и векторной базой данных вынесена за
рамки текущего скелета. Функции здесь эмулируют форму ответа, которую в
будущем будет отдавать реальный сервис, чтобы остальные микросервисы уже
сейчас могли работать против стабильного контракта.
"""


def generate_answer(question: str, context: str = "") -> str:
    prefix = f"[GigaChat STUB] " if not context else f"[GigaChat STUB, с учётом материалов] "
    return f"{prefix}Ответ на вопрос «{question}» будет сгенерирован реальной моделью."


def generate_topic_distribution(program_name: str, topics: list[str]) -> list[dict]:
    if not topics:
        return []
    share = round(100 / len(topics), 2)
    return [{"topic": topic, "weight_percent": share} for topic in topics]


def generate_questions(topic_name: str, count: int) -> list[dict]:
    questions = []
    for i in range(1, count + 1):
        questions.append(
            {
                "question_text": f"[GigaChat STUB] Вопрос {i} по теме «{topic_name}»",
                "answers": [
                    {"answer_text": "Вариант ответа A", "is_correct": True},
                    {"answer_text": "Вариант ответа B", "is_correct": False},
                ],
            }
        )
    return questions
