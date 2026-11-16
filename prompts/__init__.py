"""
Prompt Manager: every piece of text sent to the language model is built here.

Builders take plain arguments (topic, difficulty, curriculum context, weak
subtopics, question count, ...) and return chat messages. Lesson and quiz
prompts are grounded in the lecturer's curriculum guide via
build_curriculum_context.
"""
from prompts.system import SYSTEM_PROMPT
from prompts.builders import (
    build_curriculum_context,
    hint_messages,
    explanation_messages,
    grading_messages,
    chat_messages,
    personalized_quiz_messages,
    lesson_messages,
)

__all__ = [
    "SYSTEM_PROMPT",
    "build_curriculum_context",
    "hint_messages",
    "explanation_messages",
    "grading_messages",
    "chat_messages",
    "personalized_quiz_messages",
    "lesson_messages",
]
