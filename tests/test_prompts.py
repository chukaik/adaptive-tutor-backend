"""Prompt builders include what they are given."""
from prompts import (
    SYSTEM_PROMPT,
    build_curriculum_context,
    chat_messages,
    explanation_messages,
    grading_messages,
    hint_messages,
    lesson_messages,
    personalized_quiz_messages,
)

CONTEXT = "Topic: Trees\n\nSubtopic: Binary Search Trees\nLeft < root < right."


def user_text(messages):
    return messages[-1]["content"]


# ── Curriculum context ───────────────────────────────────────────────────────

def test_curriculum_context_lists_topic_and_each_subtopic():
    guide = {
        "topic_title": "Trees",
        "subtopics": [
            {"title": "Binary Search Trees", "key_content": "Left < root < right."},
            {"title": "Traversal", "key_content": "In-order visits left, root, right."},
        ],
    }
    text = build_curriculum_context(guide)
    assert text.startswith("Topic: Trees")
    assert "Subtopic: Binary Search Trees\nLeft < root < right." in text
    assert "Subtopic: Traversal\nIn-order visits left, root, right." in text


def test_curriculum_context_empty_without_guide():
    assert build_curriculum_context(None) == ""
    assert build_curriculum_context({}) == ""


def test_curriculum_context_tolerates_missing_key_content():
    text = build_curriculum_context({"topic_title": "T", "subtopics": [{"title": "S"}]})
    assert text == "Topic: T\n\nSubtopic: S\n"


# ── Personalised quiz ────────────────────────────────────────────────────────

def test_quiz_prompt_includes_context_weak_subtopics_and_count():
    messages = personalized_quiz_messages(
        topic_title="Trees",
        weak_subtopics=["Binary Search Trees", "Tree Traversal"],
        difficulty="hard",
        curriculum_context=CONTEXT,
        count=7,
    )
    text = user_text(messages)
    assert CONTEXT in text
    assert "- Binary Search Trees\n- Tree Traversal" in text
    assert "Generate exactly 7 questions" in text
    assert "TOPIC: Trees" in text
    assert "DIFFICULTY: HARD" in text
    assert "application and code analysis" in text


def test_quiz_prompt_easy_guidance():
    text = user_text(personalized_quiz_messages("T", ["S"], "easy", CONTEXT))
    assert "DIFFICULTY: EASY" in text
    assert "basic recall and definitions" in text
    assert "Generate exactly 10 questions" in text  # default count


def test_quiz_prompt_has_no_system_message():
    messages = personalized_quiz_messages("T", ["S"], "easy", CONTEXT)
    assert [m["role"] for m in messages] == ["user"]


# ── Lesson ───────────────────────────────────────────────────────────────────

def test_initial_lesson_covers_all_subtopics_with_context():
    messages = lesson_messages("Trees", ["BST", "Traversal"], CONTEXT)
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    text = user_text(messages)
    assert CONTEXT in text
    assert "- BST\n- Traversal" in text
    assert "first-time lesson" in text
    assert '"is_remedial": false' in text
    assert '"topic_title": "Trees"' in text


def test_remedial_lesson_covers_only_weak_subtopics():
    text = user_text(lesson_messages(
        "Trees", ["BST", "Traversal", "Heaps"], CONTEXT,
        is_remedial=True, weak_subtopics=["Traversal"],
    ))
    assert "REMEDIAL lesson" in text
    assert "SUBTOPICS TO COVER:\n- Traversal\n" in text
    assert "- BST" not in text
    assert '"is_remedial": true' in text
    assert CONTEXT in text


def test_remedial_without_weak_subtopics_falls_back_to_all():
    text = user_text(lesson_messages("T", ["A", "B"], CONTEXT, is_remedial=True, weak_subtopics=[]))
    assert "SUBTOPICS TO COVER:\n- A\n- B\n" in text
    assert "first-time lesson" in text


# ── Hint, explanation, grading, chat ─────────────────────────────────────────

def test_hint_includes_question_topic_and_difficulty():
    messages = hint_messages("What does push do?", "Stacks", "hard")
    assert messages[0]["content"] == SYSTEM_PROMPT
    text = user_text(messages)
    assert "this hard quiz question about Stacks" in text
    assert "Question: What does push do?" in text


def test_explanation_reflects_correctness():
    right = user_text(explanation_messages("Q", "LIFO", "LIFO", True, "Stacks"))
    wrong = user_text(explanation_messages("Q", "LIFO", "FIFO", False, "Stacks"))
    assert "correctly" in right and "incorrectly" not in right
    assert "incorrectly" in wrong
    assert "Correct Answer: LIFO" in wrong
    assert "Student's Answer: FIFO" in wrong
    assert "Topic: Stacks" in wrong


def test_grading_includes_expected_and_student_answer():
    messages = grading_messages("Define a queue.", "FIFO structure", "first in first out")
    assert [m["role"] for m in messages] == ["user"]
    text = user_text(messages)
    assert "Expected Answer: FIFO structure" in text
    assert "Student's Answer: first in first out" in text
    assert '{"is_correct": true or false' in text


def test_chat_keeps_last_ten_history_messages_and_topic():
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
               for i in range(14)]
    messages = chat_messages("next question", history, topic_context="Trees")
    assert messages[0]["role"] == "system"
    assert messages[0]["content"].startswith(SYSTEM_PROMPT)
    assert "currently studying: Trees" in messages[0]["content"]
    assert [m["content"] for m in messages[1:-1]] == [f"m{i}" for i in range(4, 14)]
    assert messages[-1] == {"role": "user", "content": "next question"}


def test_chat_without_topic_uses_plain_system_prompt():
    messages = chat_messages("hi", [])
    assert messages == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "hi"},
    ]
