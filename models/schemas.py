from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# ENUMS

class Difficulty(str, Enum):
    easy = "easy"
    hard = "hard"

class SessionType(str, Enum):
    seeded       = "seeded"
    personalized = "personalized"

class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    typed           = "typed"

class NextAction(str, Enum):
    increase_difficulty = "INCREASE_DIFFICULTY"
    unlock_next_topic   = "UNLOCK_NEXT_TOPIC"
    repeat_concept      = "REPEAT_CONCEPT"

class MasteryLevel(str, Enum):
    locked   = "locked"
    low      = "low"
    medium   = "medium"
    high     = "high"


# ONBOARDING

class OnboardingRequest(BaseModel):
    user_id:          str
    faculty:          str
    course_of_study:  str
    year_of_study:    int
    selected_course_ids: List[str]


class OnboardingResponse(BaseModel):
    success:          bool
    unlocked_topics:  List[str]
    message:          str


# QUIZ

class QuizFetchRequest(BaseModel):
    user_id:      str
    topic_id:     str
    difficulty:   Difficulty
    session_type: SessionType = SessionType.seeded


class QuestionOut(BaseModel):
    question_id:    str
    question_type:  QuestionType
    question_text:  str
    subtopic:       str
    options:        Optional[List[str]] = None  # None for typed questions


class QuizFetchResponse(BaseModel):
    session_id: str
    topic_id:   str
    difficulty: str
    questions:  List[QuestionOut]


class AnswerIn(BaseModel):
    question_id:   str
    question_type: QuestionType
    student_answer: str


class QuizSubmitRequest(BaseModel):
    session_id:  str
    user_id:     str
    topic_id:    str
    difficulty:  Difficulty
    answers:     List[AnswerIn]
    time_taken_seconds: int = 0


class QuestionResult(BaseModel):
    question_id:     str
    question_text:   str
    question_type:   QuestionType
    student_answer:  str
    correct_answer:  str
    is_correct:      bool
    explanation:     str
    subtopic:        str
    ai_reasoning:    Optional[str] = None  # Only for typed answers


class QuizSubmitResponse(BaseModel):
    session_id:         str
    score:              float
    passed:             bool
    total_questions:    int
    correct_count:      int
    next_action:        NextAction
    next_topic_id:      Optional[str]
    mastery_level:      MasteryLevel
    message:            str
    results:            List[QuestionResult]


# HINT & EXPLANATION

class HintRequest(BaseModel):
    question_text: str
    topic:         str
    difficulty:    str


class HintResponse(BaseModel):
    hint: str


class ExplainRequest(BaseModel):
    question_text:  str
    correct_answer: str
    student_answer: str
    is_correct:     bool
    topic:          str


class ExplainResponse(BaseModel):
    explanation: str


# PERSONALIZED QUIZ GENERATION

class PersonalizedQuizRequest(BaseModel):
    user_id:              str
    topic_id:             str
    difficulty:           Difficulty
    weak_subtopics:       List[str]
    previous_question_ids: List[str] = []


# CHAT

class ChatMessage(BaseModel):
    role:    str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    user_id:       str
    message:       str
    topic_context: Optional[str] = None
    history:       List[ChatMessage] = []


class ChatResponse(BaseModel):
    response:   str
    message_id: str


# PROGRESS

class TopicProgressOut(BaseModel):
    topic_id:             str
    topic_title:          str
    mastery_level:        MasteryLevel
    is_unlocked:          bool
    easy_quiz_best_score: float
    hard_quiz_best_score: float
    attempts:             int
    difficulty_unlocked:  str


class ProgressResponse(BaseModel):
    user_id:         str
    login_streak:    int
    longest_streak:  int
    topics_mastered: int
    total_topics:    int
    average_score:   float
    topics:          List[TopicProgressOut]


# STREAK

class StreakRequest(BaseModel):
    user_id: str


class StreakResponse(BaseModel):
    current_streak:  int
    longest_streak:  int
    is_new_day:      bool