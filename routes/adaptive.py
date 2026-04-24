from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.firebase_service import get_document, set_document, query_collection
from firebase_admin import firestore

router = APIRouter()


class InitCourseRequest(BaseModel):
    user_id: str
    course_id: str


@router.post("/init-course")
def init_course_progress(req: InitCourseRequest):
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    topics = query_collection(
        "topics",
        filters=[("course_id", "==", req.course_id)],
    )

    if not topics:
        raise HTTPException(status_code=404, detail="No topics found for this course")

    topics_sorted = sorted(topics, key=lambda t: t.get("order_index", 0))
    first_topic = topics_sorted[0]
    first_topic_id = first_topic.get("topic_id") or first_topic.get("id")

    if not first_topic_id:
        raise HTTPException(status_code=500, detail="First topic ID not found")

    progress_doc_id = f"{req.user_id}_{first_topic_id}"
    existing = get_document("student_progress", progress_doc_id)

    if existing:
        return {
            "message": "Course already initialised",
            "topic_id": first_topic_id,
        }

    set_document(
        "student_progress",
        progress_doc_id,
        {
            "user_id":              req.user_id,
            "course_id":            req.course_id,
            "topic_id":             first_topic_id,
            "is_unlocked":          True,
            "mastery_level":        "low",
            "difficulty_unlocked":  "easy",
            "attempts":             0,
            "accuracy":             0.0,
            "easy_quiz_best_score": 0.0,
            "hard_quiz_best_score": 0.0,
            "weak_areas":           [],
            "last_attempt_at":      firestore.SERVER_TIMESTAMP,
        }
    )

    return {
        "message":       "Course initialised successfully",
        "course_id":     req.course_id,
        "first_topic_id": first_topic_id,
        "unlocked":      True,
    }
