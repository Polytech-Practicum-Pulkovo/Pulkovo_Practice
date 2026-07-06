import contextlib
import os

import psycopg2
import psycopg2.extras

from app import config

DB_CONFIG = {
    "host": config.DB_HOST,
    "port": config.DB_PORT,
    "dbname": config.DB_NAME,
    "user": config.DB_USER,
    "password": config.DB_PASSWORD,
}


@contextlib.contextmanager
def get_cursor(commit: bool = False):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def get_topic_by_id(topic_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_topic AS id, name FROM topic WHERE id_topic = %s",
            (topic_id,),
        )
        return cur.fetchone()


def get_topic_by_name(name: str):
    with get_cursor() as cur:
        cur.execute("SELECT id_topic AS id, name FROM topic WHERE lower(name) = lower(%s)", (name,))
        return cur.fetchone()


def get_question_by_id(question_id: int):
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_question AS id, question_text AS text FROM question WHERE id_question = %s",
            (question_id,),
        )
        question = cur.fetchone()
        if not question:
            return None

        cur.execute(
            "SELECT answer_text AS text, is_correct FROM answer WHERE id_question = %s ORDER BY id_answer",
            (question_id,),
        )
        answers = cur.fetchall()

    options = [row["text"] for row in answers]
    correct_option = next(
        (index for index, row in enumerate(answers) if row["is_correct"]),
        None,
    )
    return {
        "id": question["id"],
        "text": question["text"],
        "options": options,
        "correct_option": correct_option,
    }


def get_random_question():
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_question AS id, question_text AS text FROM question ORDER BY id_question LIMIT 1"
        )
        question = cur.fetchone()
        if not question:
            return None

        cur.execute(
            "SELECT answer_text AS text, is_correct FROM answer WHERE id_question = %s ORDER BY id_answer",
            (question["id"],),
        )
        answers = cur.fetchall()

    options = [row["text"] for row in answers]
    correct_option = next(
        (index for index, row in enumerate(answers) if row["is_correct"]),
        None,
    )
    return {
        "id": question["id"],
        "text": question["text"],
        "options": options,
        "correct_option": correct_option,
    }


def get_all_topics():
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_topic AS id, name FROM topic ORDER BY id_topic"
        )
        topics = cur.fetchall()
    return [{"id": row["id"], "name": row["name"], "description": row["name"]} for row in topics]


def get_all_acts():
    with get_cursor() as cur:
        cur.execute(
            "SELECT id_learning_material AS id, file_link AS title, file_link AS text FROM learning_material ORDER BY id_learning_material"
        )
        acts = cur.fetchall()
    return [{"id": row["id"], "title": row["title"], "text": row["text"]} for row in acts]


def get_questions_for_topic(topic_name: str | None, limit: int = 5):
    if not topic_name:
        return []

    topic = get_topic_by_name(topic_name)
    if not topic:
        return []

    with get_cursor() as cur:
        cur.execute(
            "SELECT id_question AS id, question_text AS text FROM question WHERE id_topic = %s ORDER BY id_question LIMIT %s",
            (topic["id"], limit),
        )
        questions = cur.fetchall()

    result = []
    for question in questions:
        with get_cursor() as cur:
            cur.execute(
                "SELECT answer_text AS text, is_correct FROM answer WHERE id_question = %s ORDER BY id_answer",
                (question["id"],),
            )
            answers = cur.fetchall()

        options = [row["text"] for row in answers]
        correct_option = next(
            (index for index, row in enumerate(answers) if row["is_correct"]),
            None,
        )
        result.append(
            {
                "id": question["id"],
                "text": question["text"],
                "options": options,
                "correct_option": correct_option,
            }
        )

    return result


def save_generated_question(source_file: str, topic: str | None, text: str, options: list[str], correct_option: int | None):
    topic_name = topic or "Общая тема"
    existing_topic = get_topic_by_name(topic_name)
    if existing_topic is None:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "SELECT id_program FROM program ORDER BY id_program LIMIT 1"
            )
            program = cur.fetchone()
            if not program:
                raise ValueError("В базе нет ни одной программы")
            cur.execute(
                "INSERT INTO topic (id_program, name) VALUES (%s, %s) RETURNING id_topic",
                (program["id_program"], topic_name),
            )
            existing_topic = {"id": cur.fetchone()["id_topic"]}

    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO question (id_topic, question_text, is_verified) VALUES (%s, %s, false) RETURNING id_question",
            (existing_topic["id"], text),
        )
        question_id = cur.fetchone()["id_question"]

        for index, option in enumerate(options):
            cur.execute(
                "INSERT INTO answer (id_question, answer_text, is_correct) VALUES (%s, %s, %s)",
                (question_id, option, index == correct_option),
            )

    return {"topic": topic_name, "text": text}


def save_act_topic_assignment(act_id: int, topic_id: int, confidence: float | None = None, reasoning: str | None = None):
    return {"act_id": act_id, "topic_id": topic_id, "confidence": confidence, "reasoning": reasoning}
