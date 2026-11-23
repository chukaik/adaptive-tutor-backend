"""The 80% rule and mastery levels in services/adaptive_engine.py."""
import pytest

from models.schemas import MasteryLevel, NextAction
from services.adaptive_engine import PASS_THRESHOLD, compute_score, evaluate

INC = NextAction.increase_difficulty
UNLOCK = NextAction.unlock_next_topic
REPEAT = NextAction.repeat_concept
LOW, MEDIUM, HIGH = MasteryLevel.low, MasteryLevel.medium, MasteryLevel.high

HARD_UNLOCKED = "Excellent! You've mastered this topic. Next topic unlocked!"
COURSE_DONE = "Outstanding! You've completed all topics in this course!"
EASY_PASSED = "Great work! You've unlocked the hard quiz for this topic."

# score, difficulty, has_next_topic -> passed, next_action, mastery, message
CASES = [
    # Passing: exactly at, just above and well above the threshold
    (80,    "easy", True,  True,  INC,    MEDIUM, EASY_PASSED),
    (80,    "easy", False, True,  INC,    MEDIUM, EASY_PASSED),
    (100,   "easy", True,  True,  INC,    MEDIUM, EASY_PASSED),
    (100,   "easy", False, True,  INC,    MEDIUM, EASY_PASSED),
    (80,    "hard", True,  True,  UNLOCK, HIGH,   HARD_UNLOCKED),
    (80,    "hard", False, True,  UNLOCK, HIGH,   COURSE_DONE),
    (100,   "hard", True,  True,  UNLOCK, HIGH,   HARD_UNLOCKED),
    (100,   "hard", False, True,  UNLOCK, HIGH,   COURSE_DONE),
    (80.01, "hard", True,  True,  UNLOCK, HIGH,   HARD_UNLOCKED),
    # Just below the threshold fails on either difficulty
    (79.99, "easy", True,  False, REPEAT, MEDIUM, None),
    (79.99, "easy", False, False, REPEAT, MEDIUM, None),
    (79.99, "hard", True,  False, REPEAT, MEDIUM, None),
    (79.99, "hard", False, False, REPEAT, MEDIUM, None),
    # Failing ranges: 60-79.99 is medium mastery, below 60 is low
    (60,    "easy", True,  False, REPEAT, MEDIUM, None),
    (70,    "hard", True,  False, REPEAT, MEDIUM, None),
    (59.99, "easy", True,  False, REPEAT, LOW,    None),
    (50,    "hard", False, False, REPEAT, LOW,    None),
    (40,    "easy", True,  False, REPEAT, LOW,    None),
    (39.99, "hard", True,  False, REPEAT, LOW,    None),
    (10,    "easy", True,  False, REPEAT, LOW,    None),
    (0,     "hard", True,  False, REPEAT, LOW,    None),
]


@pytest.mark.parametrize(
    "score,difficulty,has_next,passed,action,mastery,message", CASES,
    ids=[f"{c[0]}-{c[1]}-{'next' if c[2] else 'last'}" for c in CASES],
)
def test_evaluate(score, difficulty, has_next, passed, action, mastery, message):
    result = evaluate(score, difficulty, has_next)
    assert result["passed"] is passed
    assert result["next_action"] == action
    assert result["mastery_level"] == mastery
    if message is not None:
        assert result["message"] == message
    else:
        assert "You need 80% to progress." in result["message"]


def test_threshold_is_80():
    assert PASS_THRESHOLD == 80.0


@pytest.mark.parametrize("score", [80, 100])
def test_unknown_difficulty_on_pass_raises(score):
    with pytest.raises(ValueError, match="Unknown quiz difficulty"):
        evaluate(score, "medium", True)


def test_failing_message_reports_rounded_score():
    assert evaluate(45, "easy", True)["message"].startswith("You scored 45%.")


@pytest.mark.xfail(strict=True, reason=(
    "BUG: a failing score of 79.5-79.99 is formatted with :.0f, so the "
    "message reads 'You scored 80%. You need 80% to progress.'"
))
def test_failing_message_never_claims_the_threshold():
    message = evaluate(79.99, "easy", True)["message"]
    assert not message.startswith("You scored 80%")


# ── compute_score ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("correct,total,expected", [
    (0, 0, 0.0),        # no questions: 0, no division by zero
    (5, 0, 0.0),
    (0, 10, 0.0),
    (8, 10, 80.0),
    (7, 10, 70.0),
    (10, 10, 100.0),
    (2, 3, 66.67),      # rounded to two decimals
    (1, 3, 33.33),
    (4, 5, 80.0),
    (7999, 10000, 79.99),
])
def test_compute_score(correct, total, expected):
    assert compute_score(correct, total) == expected


def test_compute_score_returns_float():
    assert isinstance(compute_score(8, 10), float)
