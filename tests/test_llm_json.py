"""Parsing of model replies that are meant to be JSON, and the retry/502 path."""
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from firebase_admin import auth

import main
import routes.quiz
import services.openai_service as openai_service
from models.llm_replies import GRADING_RESULT, LESSON, QUIZ_QUESTIONS
from services.llm_json import (
    InvalidReply,
    ModelReplyError,
    parse_json_reply,
    request_json,
    strip_code_fences,
)

QUESTION = {
    "question_type": "multiple_choice",
    "question_text": "Which structure is LIFO?",
    "subtopic": "Stacks",
    "options": ["A. Stack", "B. Queue", "C. Tree", "D. List"],
    "correct_answer": "A. Stack",
    "explanation": "A stack is last in, first out.",
}
TYPED = {
    "question_type": "typed",
    "question_text": "Define a queue.",
    "subtopic": "Queues",
    "correct_answer": "First in, first out.",
    "explanation": "",
}
LESSON_REPLY = {
    "topic_title": "Trees",
    "is_remedial": False,
    "introduction": "Intro",
    "subtopics": [{
        "title": "BST", "explanation": "Text", "analogy": "A",
        "code_examples": [{"description": "d", "code": "```int x;```", "output": ""}],
        "common_mistakes": ["m"], "practice_tips": ["t"],
    }],
    "lesson_summary": "Summary",
}


# ── Code fences ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [
    '```json\n{"a": 1}\n```',
    '```JSON\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
    '```json{"a": 1}```',
    'Here is the result:\n```json\n{"a": 1}\n```\nHope that helps.',
    '```json\n{"a": 1}',            # opening fence only (truncated)
    '  {"a": 1}  ',
])
def test_strip_code_fences(raw):
    assert json.loads(strip_code_fences(raw)) == {"a": 1}


# ── Parsing and shape checks ─────────────────────────────────────────────────

def test_fenced_quiz_reply_is_parsed():
    raw = "```json\n" + json.dumps([QUESTION, TYPED]) + "\n```"
    assert parse_json_reply(raw, QUIZ_QUESTIONS) == [QUESTION, TYPED]


def test_unfenced_lesson_with_backticks_inside_strings_is_kept_whole():
    raw = json.dumps(LESSON_REPLY)
    assert parse_json_reply(raw, LESSON) == LESSON_REPLY


def test_lesson_extra_fields_are_preserved():
    data = dict(LESSON_REPLY, extra_section="kept")
    assert parse_json_reply(json.dumps(data), LESSON)["extra_section"] == "kept"


def test_grading_bool_is_coerced():
    result = parse_json_reply('{"is_correct": "false", "reasoning": "r"}', GRADING_RESULT)
    assert result == {"is_correct": False, "reasoning": "r"}


@pytest.mark.parametrize("raw", [
    "",
    "   ",
    "Sorry, I cannot help with that.",
    '{"is_correct": true, "reasoning": "unterminated',
    "```json\n{bad json}\n```",
])
def test_malformed_replies_are_rejected(raw):
    with pytest.raises(InvalidReply):
        parse_json_reply(raw, GRADING_RESULT)


@pytest.mark.parametrize("schema,data", [
    (GRADING_RESULT, {"reasoning": "no verdict"}),
    (GRADING_RESULT, {"is_correct": "maybe"}),
    (GRADING_RESULT, [True]),
    (QUIZ_QUESTIONS, []),
    (QUIZ_QUESTIONS, QUESTION),                                         # object, not list
    (QUIZ_QUESTIONS, [dict(QUESTION, question_type="true_false")]),
    (QUIZ_QUESTIONS, [dict(QUESTION, options=None)]),                   # MC without options
    (QUIZ_QUESTIONS, [{k: v for k, v in QUESTION.items() if k != "correct_answer"}]),
    (LESSON, {"topic_title": "T", "subtopics": []}),
    (LESSON, {"topic_title": "T"}),
    (LESSON, {"subtopics": [{"title": "BST"}]}),                        # no explanation
])
def test_wrong_shape_is_rejected(schema, data):
    with pytest.raises(InvalidReply):
        parse_json_reply(json.dumps(data), schema)


# ── Retry ────────────────────────────────────────────────────────────────────

def replies(*texts):
    """A fake model call that returns each text in turn and counts calls."""
    queue = list(texts)
    def call():
        call.count += 1
        return queue.pop(0)
    call.count = 0
    return call


def test_valid_first_reply_calls_model_once():
    call = replies('{"is_correct": true, "reasoning": "ok"}')
    assert request_json(call, GRADING_RESULT, "grading result")["is_correct"] is True
    assert call.count == 1


def test_bad_first_reply_is_retried_once():
    call = replies("not json", '{"is_correct": false, "reasoning": "no"}')
    assert request_json(call, GRADING_RESULT, "grading result")["is_correct"] is False
    assert call.count == 2


def test_two_bad_replies_raise_readable_error():
    call = replies("not json", '{"wrong": "shape"}', "never used")
    with pytest.raises(ModelReplyError, match="unusable grading result"):
        request_json(call, GRADING_RESULT, "grading result")
    assert call.count == 2


# ── Through the service and a route ──────────────────────────────────────────

@pytest.fixture
def fake_openai(monkeypatch):
    """Replace the OpenAI client; set .replies to the texts it should return."""
    fake = MagicMock()
    state = {"replies": [], "requests": []}

    def create(**kwargs):
        state["requests"].append(kwargs)
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = state["replies"].pop(0)
        return response

    fake.chat.completions.create = create
    monkeypatch.setattr(openai_service, "client", fake)
    return state


def test_service_retries_with_identical_request(fake_openai):
    fake_openai["replies"] = ["oops", '```json\n{"is_correct": true, "reasoning": "r"}\n```']
    result = openai_service.grade_typed_answer("Q", "A", "A", course="Data Structures")
    assert result == {"is_correct": True, "reasoning": "r"}
    first, second = fake_openai["requests"]
    assert first == second


def test_route_answers_502_when_model_reply_is_unusable(fake_openai, monkeypatch):
    monkeypatch.setattr(auth, "verify_id_token", lambda token, *a, **k: {"uid": "alice"})
    docs = {("users", "alice"): {"id": "alice"},
            ("topics", "t1"): {"id": "t1", "title": "Trees", "course_id": "c1"}}
    monkeypatch.setattr(routes.quiz, "get_document", lambda c, d: docs.get((c, d)))
    added = []
    monkeypatch.setattr(routes.quiz, "add_document", lambda c, data: added.append(c) or "x")
    fake_openai["replies"] = ["not json", "[]"]

    r = TestClient(main.app).post(
        "/quiz/generate-personalized",
        json={"user_id": "alice", "topic_id": "t1", "difficulty": "easy",
              "weak_subtopics": ["BST"]},
        headers={"Authorization": "Bearer t"},
    )
    assert r.status_code == 502
    assert r.json() == {"detail": "The AI model returned an unusable quiz. Please try again."}
    assert added == []  # nothing saved
