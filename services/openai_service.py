"""
OpenAI API calls. Prompt text lives in the prompts package.
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from prompts import (
    hint_messages,
    explanation_messages,
    grading_messages,
    chat_messages,
    personalized_quiz_messages,
    lesson_messages,
)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _complete(messages: list, max_tokens: int, temperature: float) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _strip_fences(raw: str) -> str:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def get_hint(question_text: str, topic: str, difficulty: str) -> str:
    return _complete(
        hint_messages(question_text, topic, difficulty),
        max_tokens=150,
        temperature=0.5,
    )


def get_explanation(
    question_text: str,
    correct_answer: str,
    student_answer: str,
    is_correct: bool,
    topic: str
) -> str:
    return _complete(
        explanation_messages(question_text, correct_answer, student_answer, is_correct, topic),
        max_tokens=200,
        temperature=0.5,
    )


def grade_typed_answer(
    question_text: str,
    correct_answer: str,
    student_answer: str
) -> dict:
    raw = _complete(
        grading_messages(question_text, correct_answer, student_answer),
        max_tokens=100,
        temperature=0.1,
    )
    return json.loads(_strip_fences(raw))


def chat_with_tutor(
    message: str,
    history: list,
    topic_context: str = None
) -> str:
    return _complete(
        chat_messages(message, history, topic_context),
        max_tokens=500,
        temperature=0.7,
    )


def generate_personalized_questions(
    topic_title: str,
    weak_subtopics: list,
    difficulty: str,
    curriculum_context: str,
    previous_question_ids: list,
    count: int = 10
) -> list:
    # previous_question_ids is accepted for API compatibility; the prompt
    # does not use it.
    raw = _complete(
        personalized_quiz_messages(
            topic_title, weak_subtopics, difficulty, curriculum_context, count
        ),
        max_tokens=3000,
        temperature=0.8,
    )
    return json.loads(_strip_fences(raw))


def generate_lesson_content(
    topic_title: str,
    subtopics: list,
    curriculum_context: str,
    is_remedial: bool = False,
    weak_subtopics: list = None
) -> dict:
    """
    Generate deep, elaborated lesson content for a topic.
    If is_remedial=True, regenerate only weak subtopics in simpler language.
    """
    raw = _complete(
        lesson_messages(
            topic_title, subtopics, curriculum_context, is_remedial, weak_subtopics
        ),
        max_tokens=6000,
        temperature=0.6,
    )
    return json.loads(_strip_fences(raw))
