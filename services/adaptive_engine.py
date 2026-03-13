from models.schemas import NextAction, MasteryLevel

PASS_THRESHOLD = 80.0


def evaluate(
    score: float,
    difficulty: str,
    has_next_topic: bool
) -> dict:
    """
    Core adaptive logic.
    Returns the next action and new mastery level based on quiz score.
    """
    passed = score >= PASS_THRESHOLD

    if passed:
        if difficulty == "easy":
            return {
                "next_action":  NextAction.increase_difficulty,
                "mastery_level": MasteryLevel.medium,
                "passed":        True,
                "message":       "Great work! You've unlocked the hard quiz for this topic."
            }
        elif difficulty == "hard":
            if has_next_topic:
                return {
                    "next_action":  NextAction.unlock_next_topic,
                    "mastery_level": MasteryLevel.high,
                    "passed":        True,
                    "message":       "Excellent! You've mastered this topic. Next topic unlocked!"
                }
            else:
                return {
                    "next_action":  NextAction.unlock_next_topic,
                    "mastery_level": MasteryLevel.high,
                    "passed":        True,
                    "message":       "Outstanding! You've completed all topics in this course!"
                }
    else:
        # Determine mastery level based on score
        if score >= 60:
            mastery = MasteryLevel.medium
        elif score >= 40:
            mastery = MasteryLevel.low
        else:
            mastery = MasteryLevel.low

        return {
            "next_action":  NextAction.repeat_concept,
            "mastery_level": mastery,
            "passed":        False,
            "message":       (
                f"You scored {score:.0f}%. You need {PASS_THRESHOLD:.0f}% to progress. "
                f"Review the lesson and try again — you've got this!"
            )
        }


def compute_score(correct_count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((correct_count / total) * 100, 2)