"""
Expected shapes of model replies that are meant to be JSON.

These check only what the routes and the app rely on. Lesson models allow
extra fields so that everything the model writes is still saved and
returned to the app.
"""
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


# ── Grading of a typed answer ────────────────────────────────────────────────

class GradingResult(BaseModel):
    is_correct: bool
    reasoning: Optional[str] = ""


# ── Personalised quiz ────────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    question_type: Literal["multiple_choice", "typed"]
    question_text: str = Field(min_length=1)
    subtopic: str = ""
    options: Optional[list[str]] = None
    correct_answer: str = Field(min_length=1)
    explanation: str = ""

    @model_validator(mode="after")
    def multiple_choice_needs_options(self):
        if self.question_type == "multiple_choice" and not self.options:
            raise ValueError("multiple_choice question has no options")
        return self


QuizQuestionList = Annotated[list[QuizQuestion], Field(min_length=1)]


# ── Lesson ───────────────────────────────────────────────────────────────────

class LessonSubtopic(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    explanation: str


class Lesson(BaseModel):
    model_config = ConfigDict(extra="allow")

    topic_title: str = ""
    introduction: str = ""
    subtopics: Annotated[list[LessonSubtopic], Field(min_length=1)]
    lesson_summary: str = ""


GRADING_RESULT = TypeAdapter(GradingResult)
QUIZ_QUESTIONS = TypeAdapter(QuizQuestionList)
LESSON         = TypeAdapter(Lesson)
