"""
OpenAI API calls. Prompt text lives in the prompts package.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

from services import llm_settings
from services.llm_settings import CallSettings
from services.llm_json import request_json
from models.llm_replies import GRADING_RESULT, QUIZ_QUESTIONS, LESSON

from prompts import (
    hint_messages,
    explanation_messages,
    grading_messages,
    chat_messages,
    personalized_quiz_messages,
    lesson_messages,
)

load_dotenv()

# Created on first use so that importing this module needs no API key.
client = None


def _get_client() -> OpenAI:
    global client
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client


def _complete(messages: list, settings: CallSettings) -> str:
    response = _get_client().chat.completions.create(
        model=llm_settings.MODEL,
        messages=messages,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )
    return response.choices[0].message.content.strip()


def get_hint(question_text: str, topic: str, difficulty: str) -> str:
    return _complete(
        hint_messages(question_text, topic, difficulty),
        llm_settings.HINT,
    )


def get_explanation(
    question_text: str,
    correct_answer: str,
    student_answer: str,
    is_correct: bool,
    topic: str,
    *,
    course: str
) -> str:
    return _complete(
        explanation_messages(question_text, correct_answer, student_answer, is_correct, topic,
                             course=course),
        llm_settings.EXPLANATION,
    )


def grade_typed_answer(
    question_text: str,
    correct_answer: str,
    student_answer: str,
    *,
    course: str
) -> dict:
    messages = grading_messages(question_text, correct_answer, student_answer, course=course)
    return request_json(
        lambda: _complete(messages, llm_settings.GRADING),
        GRADING_RESULT,
        what="grading result",
    )


def chat_with_tutor(
    message: str,
    history: list,
    topic_context: str = None
) -> str:
    return _complete(
        chat_messages(message, history, topic_context),
        llm_settings.CHAT,
    )


def generate_personalized_questions(
    topic_title: str,
    weak_subtopics: list,
    difficulty: str,
    curriculum_context: str,
    previous_question_ids: list,
    count: int = 10,
    *,
    course: str
) -> list:
    # previous_question_ids is accepted for API compatibility; the prompt
    # does not use it.
    messages = personalized_quiz_messages(
        topic_title, weak_subtopics, difficulty, curriculum_context, count,
        course=course,
    )
    return request_json(
        lambda: _complete(messages, llm_settings.QUIZ),
        QUIZ_QUESTIONS,
        what="quiz",
    )


def generate_lesson_content(
    topic_title: str,
    subtopics: list,
    curriculum_context: str,
    is_remedial: bool = False,
    weak_subtopics: list = None,
    *,
    course: str
) -> dict:
    """
    Generate deep, elaborated lesson content for a topic.
    If is_remedial=True, regenerate only weak subtopics in simpler language.
    """
    messages = lesson_messages(
        topic_title, subtopics, curriculum_context, is_remedial, weak_subtopics,
        course=course,
    )
    return request_json(
        lambda: _complete(messages, llm_settings.LESSON),
        LESSON,
        what="lesson",
    )
