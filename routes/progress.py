from fastapi import APIRouter, HTTPException
from models.schemas import ProgressResponse, TopicProgressOut, MasteryLevel, StreakRequest, StreakResponse
from services.firebase_service import (
    get_document, query_collection, update_document
)
from firebase_admin import firestore
from datetime import datetime, date, timezone

router = APIRouter()


@router.get("/learning-state/{user_id}/{course_id}")
def get_learning_state(user_id: str, course_id: str):

    # Verify user exists
    user = get_document("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch all topics for this course
    topics = query_collection("topics", [("course_id", "==", course_id)])
    if not topics:
        raise HTTPException(status_code=404, detail="No topics found for this course")

    topics.sort(key=lambda t: t.get("order_index", 0))

    # Fetch student_progress for each topic
    result = []

    for topic in topics:
        topic_id        = topic["id"]
        progress_doc_id = f"{user_id}_{topic_id}"
        progress        = get_document("student_progress", progress_doc_id)

        if progress:
            result.append({
                "topic_id":             topic_id,
                "topic_title":          topic.get("title", ""),
                "mastery_level":        progress.get("mastery_level", "locked"),
                "is_unlocked":          progress.get("is_unlocked", False),
                "easy_quiz_best_score": progress.get("easy_quiz_best_score", 0.0),
                "hard_quiz_best_score": progress.get("hard_quiz_best_score", 0.0),
                "attempts":             progress.get("attempts", 0),
                "difficulty_unlocked":  progress.get("difficulty_unlocked", "easy"),
            })
        else:
            # Progress doc doesn't exist yet — treat as locked
            result.append({
                "topic_id":             topic_id,
                "topic_title":          topic.get("title", ""),
                "mastery_level":        "locked",
                "is_unlocked":          False,
                "easy_quiz_best_score": 0.0,
                "hard_quiz_best_score": 0.0,
                "attempts":             0,
                "difficulty_unlocked":  "easy",
            })

    return {
        "user_id":   user_id,
        "course_id": course_id,
        "topics":    result
    }


@router.get("/{user_id}", response_model=ProgressResponse)
def get_full_progress(user_id: str):

    # Verify user exists
    user = get_document("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch all student_progress docs for this user
    all_progress = query_collection("student_progress", [
        ("user_id", "==", user_id)
    ])

    topics_mastered = 0
    total_scores    = []
    topics_out      = []

    for p in all_progress:
        mastery = p.get("mastery_level", "locked")
        if mastery == "high":
            topics_mastered += 1

        easy_score = p.get("easy_quiz_best_score", 0.0)
        hard_score = p.get("hard_quiz_best_score", 0.0)

        if easy_score > 0:
            total_scores.append(easy_score)
        if hard_score > 0:
            total_scores.append(hard_score)

        # Fetch topic title
        topic = get_document("topics", p.get("topic_id", ""))
        topic_title = topic.get("title", "") if topic else ""

        topics_out.append(TopicProgressOut(
            topic_id             = p.get("topic_id", ""),
            topic_title          = topic_title,
            mastery_level        = mastery,
            is_unlocked          = p.get("is_unlocked", False),
            easy_quiz_best_score = easy_score,
            hard_quiz_best_score = hard_score,
            attempts             = p.get("attempts", 0),
            difficulty_unlocked  = p.get("difficulty_unlocked", "easy"),
        ))

    average_score = round(sum(total_scores) / len(total_scores), 2) if total_scores else 0.0

    return ProgressResponse(
        user_id         = user_id,
        login_streak    = user.get("login_streak", 0),
        longest_streak  = user.get("longest_streak", 0),
        topics_mastered = topics_mastered,
        total_topics    = len(all_progress),
        average_score   = average_score,
        topics          = topics_out,
    )


@router.post("/streak/update", response_model=StreakResponse)
def update_streak(req: StreakRequest):

    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today            = date.today()
    current_streak   = user.get("login_streak", 0)
    longest_streak   = user.get("longest_streak", 0)
    last_login       = user.get("last_login_date")
    is_new_day       = False

    if last_login:
        # Convert Firestore timestamp to date
        if hasattr(last_login, "date"):
            last_date = last_login.date()
        else:
            last_date = datetime.fromisoformat(str(last_login)).date()

        delta = (today - last_date).days

        if delta == 0:
            # Same day login — no change
            pass
        elif delta == 1:
            # Consecutive day — increment streak
            current_streak += 1
            is_new_day      = True
        else:
            # Missed a day — reset streak
            current_streak = 1
            is_new_day     = True
    else:
        # First ever login
        current_streak = 1
        is_new_day     = True

    if current_streak > longest_streak:
        longest_streak = current_streak

    if is_new_day:
        update_document("users", req.user_id, {
            "login_streak":    current_streak,
            "longest_streak":  longest_streak,
            "last_login_date": firestore.SERVER_TIMESTAMP,
        })

    return StreakResponse(
        current_streak = current_streak,
        longest_streak = longest_streak,
        is_new_day     = is_new_day,
    )