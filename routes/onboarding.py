from fastapi import APIRouter, HTTPException
from models.schemas import OnboardingRequest, OnboardingResponse
from services.firebase_service import (
    get_document, set_document, update_document, query_collection
)
from firebase_admin import firestore

router = APIRouter()


@router.post("/complete", response_model=OnboardingResponse)
def complete_onboarding(req: OnboardingRequest):

    # Verify user exists in Firebase Auth / users collection
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user profile with onboarding data
    update_document("users", req.user_id, {
        "faculty":             req.faculty,
        "course_of_study":     req.course_of_study,
        "year_of_study":       req.year_of_study,
        "onboarding_complete": True,
        "updated_at":          firestore.SERVER_TIMESTAMP,
    })

    # For each selected course, fetch its topics
    unlocked_topic_ids = []

    for course_id in req.selected_course_ids:

        # Get all topics for this course ordered by order_index
        topics = query_collection("topics", [
            ("course_id", "==", course_id)
        ])

        if not topics:
            continue

        # Sort topics by order_index
        topics.sort(key=lambda t: t.get("order_index", 0))

        for i, topic in enumerate(topics):
            topic_id    = topic["id"]
            is_first    = (i == 0)
            is_unlocked = is_first  # Only first topic unlocked at start

            progress_doc_id = f"{req.user_id}_{topic_id}"

            # Check if progress doc already exists — don't overwrite
            existing = get_document("student_progress", progress_doc_id)
            if existing:
                if is_unlocked:
                    unlocked_topic_ids.append(topic_id)
                continue

            # Create fresh student_progress document for this topic
            set_document("student_progress", progress_doc_id, {
                "user_id":              req.user_id,
                "topic_id":             topic_id,
                "course_id":            course_id,
                "mastery_level":        "low" if is_first else "locked",
                "easy_quiz_best_score": 0.0,
                "hard_quiz_best_score": 0.0,
                "attempts":             0,
                "accuracy":             0.0,
                "weak_areas":           [],
                "difficulty_unlocked":  "easy",
                "is_unlocked":          is_unlocked,
                "last_attempt_at":      firestore.SERVER_TIMESTAMP,
            })

            if is_unlocked:
                unlocked_topic_ids.append(topic_id)

    return OnboardingResponse(
        success=True,
        unlocked_topics=unlocked_topic_ids,
        message="Onboarding complete. Your learning journey has begun!"
    )