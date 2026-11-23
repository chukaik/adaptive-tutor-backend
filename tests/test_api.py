"""
API tests: the learning flow end to end, with Firestore and OpenAI replaced
by in-memory fakes (see conftest.py).
"""
import json

import pytest
from fastapi.testclient import TestClient

import main
from tests.conftest import bearer

COURSE = "c1"
T1, T2 = "t1", "t2"
CORRECT = "A. Right"
STACKS, QUEUES = "Stack Data Structure", "Queue Data Structure"


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def course(db):
    """A user, a two-topic course, a curriculum guide and a question bank."""
    db.put("users", "alice", {"name": "Alice"})
    db.put("users", "bob", {"name": "Bob"})
    db.put("courses", COURSE, {"title": "Data Structures", "course_code": "CSC301"})
    db.put("topics", T1, {"title": "Memory, Stacks & Queues", "course_id": COURSE, "order_index": 1})
    db.put("topics", T2, {"title": "Trees", "course_id": COURSE, "order_index": 2})
    db.put("curriculum_guides", T1, {
        "topic_title": "Memory, Stacks & Queues",
        "subtopics": [
            {"title": STACKS, "key_content": "CCMAS CURRICULUM NOTES: LIFO, push, pop."},
            {"title": QUEUES, "key_content": "CCMAS CURRICULUM NOTES: FIFO, enqueue, dequeue."},
        ],
    })
    for difficulty in ("easy", "hard"):
        for i in range(10):
            db.put("question_bank", f"{difficulty}{i}", {
                "topic_id": T1, "course_id": COURSE, "difficulty": difficulty,
                "question_type": "multiple_choice",
                "question_text": f"{difficulty} question {i}",
                "subtopic": STACKS if i % 2 == 0 else QUEUES,
                "options": [CORRECT, "B. Wrong", "C. Wrong", "D. Wrong"],
                "correct_answer": CORRECT,
                "explanation": "Because.",
                "times_used": 0, "times_correct": 0,
            })
    return db


def onboard(client, uid="alice"):
    return client.post("/onboarding/complete", headers=bearer(uid), json={
        "user_id": uid, "faculty": "Science", "course_of_study": "Computer Science",
        "year_of_study": 3, "selected_course_ids": [COURSE],
    })


def fetch(client, difficulty, uid="alice", topic=T1):
    return client.post("/quiz/fetch", headers=bearer(uid), json={
        "user_id": uid, "topic_id": topic, "difficulty": difficulty,
    })


def submit(client, session, difficulty, wrong=(), uid="alice", answers=None):
    """Answer every question in a fetched quiz; question ids in `wrong` get a wrong answer."""
    if answers is None:
        answers = [
            {"question_id": q["question_id"], "question_type": q["question_type"],
             "student_answer": "B. Wrong" if q["question_id"] in wrong else CORRECT}
            for q in session["questions"]
        ]
    return client.post("/quiz/submit", headers=bearer(uid), json={
        "session_id": session["session_id"], "user_id": uid, "topic_id": session["topic_id"],
        "difficulty": difficulty, "answers": answers, "time_taken_seconds": 120,
    })


# ── Starting a course ────────────────────────────────────────────────────────

def test_onboarding_unlocks_only_the_first_topic(client, course):
    r = onboard(client)
    assert r.status_code == 200
    assert r.json()["unlocked_topics"] == [T1]
    assert course.doc("users", "alice")["onboarding_complete"] is True
    first, second = course.doc("student_progress", f"alice_{T1}"), course.doc("student_progress", f"alice_{T2}")
    assert first["is_unlocked"] is True and first["difficulty_unlocked"] == "easy"
    assert second["is_unlocked"] is False and second["mastery_level"] == "locked"


def test_onboarding_twice_does_not_reset_progress(client, course):
    onboard(client)
    course.docs[("student_progress", f"alice_{T1}")]["attempts"] = 3
    assert onboard(client).status_code == 200
    assert course.doc("student_progress", f"alice_{T1}")["attempts"] == 3


def test_init_course_unlocks_first_topic_once(client, course):
    r = client.post("/adaptive/init-course", headers=bearer("alice"),
                    json={"user_id": "alice", "course_id": COURSE})
    assert r.status_code == 200
    assert r.json()["first_topic_id"] == T1
    assert course.doc("student_progress", f"alice_{T1}")["is_unlocked"] is True
    again = client.post("/adaptive/init-course", headers=bearer("alice"),
                        json={"user_id": "alice", "course_id": COURSE})
    assert again.json()["message"] == "Course already initialised"


def test_fetched_quiz_hides_correct_answers(client, course):
    onboard(client)
    r = fetch(client, "easy")
    assert r.status_code == 200
    body = r.json()
    assert len(body["questions"]) == 10
    assert all("correct_answer" not in q for q in body["questions"])
    session = course.doc("quiz_sessions", body["session_id"])
    assert session["user_id"] == "alice" and session["difficulty"] == "easy"


# ── Passing: easy unlocks hard, hard unlocks the next topic ──────────────────

def test_passing_easy_unlocks_hard_then_hard_unlocks_next_topic(client, course):
    onboard(client)

    # Hard is refused before easy is passed
    assert fetch(client, "hard").status_code == 403

    easy = fetch(client, "easy").json()
    r = submit(client, easy, "easy", wrong={easy["questions"][0]["question_id"],
                                             easy["questions"][1]["question_id"]})
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 80.0
    assert body["passed"] is True
    assert body["next_action"] == "INCREASE_DIFFICULTY"
    assert body["mastery_level"] == "medium"
    assert body["next_topic_id"] is None
    progress = course.doc("student_progress", f"alice_{T1}")
    assert progress["difficulty_unlocked"] == "hard"
    assert progress["easy_quiz_best_score"] == 80.0
    assert course.doc("student_progress", f"alice_{T2}")["is_unlocked"] is False

    hard = fetch(client, "hard")
    assert hard.status_code == 200
    r = submit(client, hard.json(), "hard")
    body = r.json()
    assert body["score"] == 100.0
    assert body["passed"] is True
    assert body["next_action"] == "UNLOCK_NEXT_TOPIC"
    assert body["mastery_level"] == "high"
    assert body["next_topic_id"] == T2
    assert course.doc("student_progress", f"alice_{T1}")["difficulty_unlocked"] == "completed"
    assert course.doc("student_progress", f"alice_{T2}")["is_unlocked"] is True

    state = client.get(f"/progress/learning-state/alice/{COURSE}", headers=bearer("alice")).json()
    assert [(t["topic_id"], t["is_unlocked"]) for t in state["topics"]] == [(T1, True), (T2, True)]


def test_passing_hard_on_last_topic_completes_course(client, course):
    onboard(client)
    course.docs[("student_progress", f"alice_{T2}")].update(is_unlocked=True, difficulty_unlocked="hard")
    for i in range(10):
        course.put("question_bank", f"t2hard{i}", {
            "topic_id": T2, "difficulty": "hard", "question_type": "multiple_choice",
            "question_text": "q", "subtopic": "Trees", "options": [CORRECT],
            "correct_answer": CORRECT, "explanation": "",
        })
    session = fetch(client, "hard", topic=T2).json()
    body = submit(client, session, "hard").json()
    assert body["passed"] is True
    assert body["next_topic_id"] is None
    assert body["message"] == "Outstanding! You've completed all topics in this course!"


def test_typed_answers_are_graded_by_the_model(client, course, openai):
    onboard(client)
    for i in range(2):
        course.put("question_bank", f"typed{i}", {
            "topic_id": T1, "difficulty": "easy", "question_type": "typed",
            "question_text": "What does LIFO mean?", "subtopic": STACKS,
            "correct_answer": "Last in, first out", "explanation": "",
        })
    session = {"session_id": course.collection("quiz_sessions").add(
        {"user_id": "alice", "topic_id": T1, "difficulty": "easy",
         "questions": ["typed0", "typed1"], "answers_submitted": []})[1].id, "topic_id": T1}
    openai.replies = ['```json\n{"is_correct": true, "reasoning": "Same meaning."}\n```',
                      '{"is_correct": false, "reasoning": "Describes a queue."}']
    answers = [{"question_id": "typed0", "question_type": "typed", "student_answer": "last one in leaves first"},
               {"question_id": "typed1", "question_type": "typed", "student_answer": "first in first out"}]
    body = submit(client, session, "easy", answers=answers).json()
    assert [r["is_correct"] for r in body["results"]] == [True, False]
    assert body["results"][0]["ai_reasoning"] == "Same meaning."
    assert body["score"] == 50.0
    assert "Student's Answer: first in first out" in openai.requests[1]["messages"][-1]["content"]
    # The course is named from the course document
    assert "an undergraduate Data Structures student" in openai.requests[1]["messages"][-1]["content"]


# ── Failing: weak subtopics come back, remedial lesson and quiz use them ─────

def test_failing_returns_weak_subtopics_and_keeps_topic_locked(client, course, openai):
    onboard(client)
    easy = fetch(client, "easy").json()
    queue_ids = {q["question_id"] for q in easy["questions"] if q["subtopic"] == QUEUES}
    assert len(queue_ids) == 5

    body = submit(client, easy, "easy", wrong=queue_ids).json()
    assert body["score"] == 50.0
    assert body["passed"] is False
    assert body["next_action"] == "REPEAT_CONCEPT"
    assert body["mastery_level"] == "low"
    wrong = [r for r in body["results"] if not r["is_correct"]]
    assert {r["subtopic"] for r in wrong} == {QUEUES}
    assert all(r["correct_answer"] == CORRECT for r in wrong)

    progress = course.doc("student_progress", f"alice_{T1}")
    assert progress["weak_areas"] == [QUEUES]
    assert progress["difficulty_unlocked"] == "easy"
    assert progress["easy_quiz_best_score"] == 50.0
    assert progress["attempts"] == 1
    assert set(course.doc("quiz_sessions", easy["session_id"])["weak_question_ids"]) == queue_ids
    assert course.doc("student_progress", f"alice_{T2}")["is_unlocked"] is False
    assert fetch(client, "hard").status_code == 403

    # Remedial lesson covers only the weak subtopic, grounded in the curriculum
    openai.replies = [json.dumps({"topic_title": "Memory, Stacks & Queues", "subtopics": [
        {"title": QUEUES, "explanation": "A queue is FIFO."}]})]
    r = client.post("/lesson/remedial", headers=bearer("alice"),
                    json={"user_id": "alice", "topic_id": T1, "weak_subtopics": [QUEUES]})
    assert r.status_code == 200
    assert r.json()["weak_subtopics"] == [QUEUES]
    prompt = openai.requests[-1]["messages"][-1]["content"]
    assert f"SUBTOPICS TO COVER:\n- {QUEUES}\n" in prompt
    assert "FIFO, enqueue, dequeue" in prompt
    assert "You are an expert Data Structures programming lecturer" in prompt
    assert "Java" not in prompt
    assert course.doc("user_lessons", f"alice_{T1}_remedial")["is_remedial"] is True

    # Personalised quiz targets the weak subtopic and is saved to the bank
    openai.replies = [json.dumps([{
        "question_type": "multiple_choice", "question_text": "Which end does dequeue use?",
        "subtopic": QUEUES, "options": ["A. Front", "B. Back"], "correct_answer": "A. Front",
        "explanation": "FIFO."}])]
    r = client.post("/quiz/generate-personalized", headers=bearer("alice"), json={
        "user_id": "alice", "topic_id": T1, "difficulty": "easy", "weak_subtopics": [QUEUES]})
    assert r.status_code == 200
    new_q = r.json()["questions"][0]
    assert "correct_answer" not in new_q
    saved = course.doc("question_bank", new_q["question_id"])
    assert saved["source"] == "ai_generated" and saved["correct_answer"] == "A. Front"
    assert f"- {QUEUES}" in openai.requests[-1]["messages"][-1]["content"]
    assert "in a Data Structures programming course" in openai.requests[-1]["messages"][-1]["content"]


def test_failing_keeps_best_score(client, course):
    onboard(client)
    course.docs[("student_progress", f"alice_{T1}")]["easy_quiz_best_score"] = 70.0
    easy = fetch(client, "easy").json()
    ids = [q["question_id"] for q in easy["questions"]]
    submit(client, easy, "easy", wrong=set(ids[:6]))
    assert course.doc("student_progress", f"alice_{T1}")["easy_quiz_best_score"] == 70.0


def test_lesson_is_generated_once_then_served_from_storage(client, course, openai):
    onboard(client)
    openai.replies = [json.dumps({"subtopics": [{"title": STACKS, "explanation": "LIFO."}]})]
    first = client.post("/lesson/fetch", headers=bearer("alice"), json={"user_id": "alice", "topic_id": T1})
    second = client.post("/lesson/fetch", headers=bearer("alice"), json={"user_id": "alice", "topic_id": T1})
    assert first.json()["source"] == "generated"
    assert second.json()["source"] == "saved"
    assert second.json()["lesson"] == first.json()["lesson"]
    assert len(openai.requests) == 1


def test_chat_saves_both_messages_in_a_session(client, course, openai):
    openai.replies = ["A stack is LIFO."]
    r = client.post("/chat/message", headers=bearer("alice"),
                    json={"user_id": "alice", "message": "What is a stack?"})
    assert r.status_code == 200
    session_id = r.json()["session_id"]
    history = client.get(f"/chat/history/alice?session_id={session_id}", headers=bearer("alice")).json()
    assert [(m["role"], m["content"]) for m in history["messages"]] == [
        ("user", "What is a stack?"), ("assistant", "A stack is LIFO.")]
    sessions = client.get("/chat/sessions/alice", headers=bearer("alice")).json()["sessions"]
    assert sessions[0]["title"] == "What is a stack?"


# ── Rejected requests ────────────────────────────────────────────────────────

def test_no_token_is_401(client, course):
    r = client.post("/quiz/fetch", json={"user_id": "alice", "topic_id": T1, "difficulty": "easy"})
    assert r.status_code == 401
    assert course.all("quiz_sessions") == {}


def test_another_users_id_is_403(client, course):
    onboard(client)
    r = client.post("/quiz/fetch", headers=bearer("bob"),
                    json={"user_id": "alice", "topic_id": T1, "difficulty": "easy"})
    assert r.status_code == 403
    assert client.get("/progress/alice", headers=bearer("bob")).status_code == 403
    assert client.get("/chat/history/alice", headers=bearer("bob")).status_code == 403


def test_submitting_another_users_session_is_403(client, course):
    onboard(client)
    onboard(client, "bob")
    alices = fetch(client, "easy").json()
    r = submit(client, alices, "easy", uid="bob")
    assert r.status_code == 403
    assert course.doc("quiz_sessions", alices["session_id"])["answers_submitted"] == []


def test_locked_topic_is_403(client, course):
    onboard(client)
    assert fetch(client, "easy", topic=T2).status_code == 403
    r = client.post("/lesson/fetch", headers=bearer("alice"), json={"user_id": "alice", "topic_id": T2})
    assert r.status_code == 403


def test_not_onboarded_topic_is_403(client, course):
    assert fetch(client, "easy").status_code == 403


def test_unknown_session_is_404(client, course):
    onboard(client)
    r = submit(client, {"session_id": "nope", "topic_id": T1, "questions": []}, "easy")
    assert r.status_code == 404


def test_unknown_user_is_404(client, course):
    r = client.post("/quiz/fetch", headers=bearer("carol"),
                    json={"user_id": "carol", "topic_id": T1, "difficulty": "easy"})
    assert r.status_code == 404


def test_invalid_difficulty_is_422(client, course):
    onboard(client)
    r = client.post("/quiz/fetch", headers=bearer("alice"),
                    json={"user_id": "alice", "topic_id": T1, "difficulty": "medium"})
    assert r.status_code == 422


def test_remedial_lesson_without_weak_subtopics_is_400(client, course, openai):
    r = client.post("/lesson/remedial", headers=bearer("alice"),
                    json={"user_id": "alice", "topic_id": T1, "weak_subtopics": []})
    assert r.status_code == 400
    assert openai.requests == []


def test_unusable_model_reply_is_502(client, course, openai):
    onboard(client)
    openai.replies = ["Sorry, I can't.", "Still not JSON."]
    r = client.post("/lesson/fetch", headers=bearer("alice"), json={"user_id": "alice", "topic_id": T1})
    assert r.status_code == 502
    assert course.doc("user_lessons", f"alice_{T1}_initial") is None


# ── Grading against the quiz session ─────────────────────────────────────────

def answer(question, student_answer=CORRECT, question_type=None):
    return {"question_id": question["question_id"],
            "question_type": question_type or question["question_type"],
            "student_answer": student_answer}


def assert_nothing_recorded(db, session_id):
    assert db.doc("quiz_sessions", session_id)["answers_submitted"] == []
    assert db.doc("student_progress", f"alice_{T1}")["attempts"] == 0


def test_submitting_a_subset_of_questions_does_not_pass(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    one = easy["questions"][0]
    r = submit(client, easy, "easy", answers=[{
        "question_id": one["question_id"], "question_type": one["question_type"],
        "student_answer": CORRECT}])
    assert r.json()["passed"] is False


def test_unanswered_questions_count_as_wrong(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    first = easy["questions"][0]
    body = submit(client, easy, "easy", answers=[answer(first)]).json()
    assert body["total_questions"] == 10
    assert body["correct_count"] == 1
    assert body["score"] == 10.0
    assert len(body["results"]) == 10
    unanswered = [r for r in body["results"] if r["question_id"] != first["question_id"]]
    assert all(r["student_answer"] == "" and not r["is_correct"] for r in unanswered)
    stored = course.doc("quiz_sessions", easy["session_id"])["answers_submitted"]
    assert [a["question_id"] for a in stored] == [q["question_id"] for q in easy["questions"]]


def test_easy_session_submitted_as_hard_does_not_unlock_next_topic(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    r = submit(client, easy, "hard")
    assert r.status_code in (400, 403) or r.json()["next_action"] != "UNLOCK_NEXT_TOPIC"


def test_difficulty_that_disagrees_with_session_is_400(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    r = submit(client, easy, "hard")
    assert r.status_code == 400
    assert "difficulty" in r.json()["detail"]
    assert_nothing_recorded(course, easy["session_id"])


def test_topic_that_disagrees_with_session_is_400(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    r = submit(client, {**easy, "topic_id": T2}, "easy")
    assert r.status_code == 400
    assert "topic_id" in r.json()["detail"]
    assert_nothing_recorded(course, easy["session_id"])


def test_answer_for_question_not_in_session_is_400(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    in_session = {q["question_id"] for q in easy["questions"]}
    outsider = next(f"hard{i}" for i in range(10) if f"hard{i}" not in in_session)
    answers = [answer(q) for q in easy["questions"]]
    answers[0]["question_id"] = outsider
    r = submit(client, easy, "easy", answers=answers)
    assert r.status_code == 400
    assert outsider in r.json()["detail"]
    assert_nothing_recorded(course, easy["session_id"])


def test_duplicate_answer_is_400(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    first = easy["questions"][0]
    r = submit(client, easy, "easy",
               answers=[answer(first), answer(first, "B. Wrong")])
    assert r.status_code == 400
    assert "more than once" in r.json()["detail"]
    assert_nothing_recorded(course, easy["session_id"])


def test_session_without_questions_is_400(client, course):
    onboard(client)
    session_id = course.collection("quiz_sessions").add({
        "user_id": "alice", "topic_id": T1, "difficulty": "easy",
        "questions": [], "answers_submitted": []})[1].id
    r = submit(client, {"session_id": session_id, "topic_id": T1, "questions": []}, "easy")
    assert r.status_code == 400


def test_submitting_a_session_twice_is_409(client, course):
    onboard(client)
    easy = fetch(client, "easy").json()
    assert submit(client, easy, "easy").status_code == 200
    first = course.doc("quiz_sessions", easy["session_id"])["answers_submitted"]
    wrong = {q["question_id"] for q in easy["questions"]}
    r = submit(client, easy, "easy", wrong=wrong)
    assert r.status_code == 409
    assert course.doc("quiz_sessions", easy["session_id"])["answers_submitted"] == first
    assert course.doc("student_progress", f"alice_{T1}")["attempts"] == 1


def test_question_type_comes_from_the_question_bank(client, course, openai):
    onboard(client)
    easy = fetch(client, "easy").json()
    # Every stored question is multiple choice; claiming "typed" must not
    # send the answer to the model for lenient grading.
    answers = [answer(q, "a. right", question_type="typed") for q in easy["questions"]]
    body = submit(client, easy, "easy", answers=answers).json()
    assert body["score"] == 100.0
    assert {r["question_type"] for r in body["results"]} == {"multiple_choice"}
    assert openai.requests == []
