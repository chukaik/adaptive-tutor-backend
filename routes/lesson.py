from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.firebase_service import (
    get_document, set_document, query_collection
)
from services.openai_service import generate_lesson_content
from firebase_admin import firestore

router = APIRouter()


# SCHEMAS

class LessonRequest(BaseModel):
    user_id:   str
    topic_id:  str


class RemedialLessonRequest(BaseModel):
    user_id:         str
    topic_id:        str
    weak_subtopics:  List[str]


# HELPER

def fetch_curriculum_context(topic_id: str) -> tuple:
    """Returns (curriculum_context_string, subtopics_list)"""
    doc = get_document("curriculum_guides", topic_id)
    if not doc:
        return "", []

    lines     = [f"Topic: {doc.get('topic_title', '')}"]
    subtopics = []

    for sub in doc.get("subtopics", []):
        lines.append(f"\nSubtopic: {sub['title']}")
        lines.append(sub.get("key_content", ""))
        subtopics.append(sub["title"])

    return "\n".join(lines), subtopics


def save_lesson(user_id: str, topic_id: str, lesson_data: dict, is_remedial: bool):
    """Save generated lesson to Firestore under the user's lessons collection."""
    doc_id = f"{user_id}_{topic_id}_{'remedial' if is_remedial else 'initial'}"
    set_document("user_lessons", doc_id, {
        "user_id":     user_id,
        "topic_id":    topic_id,
        "is_remedial": is_remedial,
        "lesson":      lesson_data,
        "created_at":  firestore.SERVER_TIMESTAMP,
    })
    return doc_id


# ENDPOINTS

@router.post("/fetch")
def fetch_lesson(req: LessonRequest):
    """
    Fetch lesson for a topic.
    Returns saved lesson if it exists, otherwise generates a new one.
    """

    # Verify user and topic
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    topic = get_document("topics", req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Verify topic is unlocked
    progress_doc_id = f"{req.user_id}_{req.topic_id}"
    progress = get_document("student_progress", progress_doc_id)
    if not progress or not progress.get("is_unlocked", False):
        raise HTTPException(
            status_code=403,
            detail="This topic is locked. Complete the prerequisite topic first."
        )

    # Check if lesson already exists for this user
    existing_doc_id = f"{req.user_id}_{req.topic_id}_initial"
    existing_lesson = get_document("user_lessons", existing_doc_id)

    if existing_lesson:
        return {
            "source":  "saved",
            "lesson":  existing_lesson.get("lesson"),
            "message": "Lesson loaded from your saved content."
        }

    # Generate new lesson
    curriculum_context, subtopics = fetch_curriculum_context(req.topic_id)

    if not curriculum_context:
        raise HTTPException(
            status_code=500,
            detail="Curriculum guide not found for this topic."
        )

    lesson_data = generate_lesson_content(
        topic_title        = topic.get("title", ""),
        subtopics          = subtopics,
        curriculum_context = curriculum_context,
        is_remedial        = False,
    )

    # Save lesson for this user
    save_lesson(req.user_id, req.topic_id, lesson_data, is_remedial=False)

    return {
        "source":  "generated",
        "lesson":  lesson_data,
        "message": "Lesson generated successfully."
    }


@router.post("/remedial")
def fetch_remedial_lesson(req: RemedialLessonRequest):
    """
    Generate a remedial lesson targeting only the student's weak subtopics.
    Called after a student fails a quiz.
    Always generates fresh — never returns cached for remedial.
    """

    # Verify user and topic
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    topic = get_document("topics", req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if not req.weak_subtopics:
        raise HTTPException(
            status_code=400,
            detail="No weak subtopics provided for remedial lesson."
        )

    # Fetch curriculum context1
    curriculum_context, all_subtopics = fetch_curriculum_context(req.topic_id)

    if not curriculum_context:
        raise HTTPException(
            status_code=500,
            detail="Curriculum guide not found for this topic."
        )

    # Generate remedial lesson
    lesson_data = generate_lesson_content(
        topic_title        = topic.get("title", ""),
        subtopics          = all_subtopics,
        curriculum_context = curriculum_context,
        is_remedial        = True,
        weak_subtopics     = req.weak_subtopics,
    )

    # Save remedial lesson
    # Each remedial lesson overwrites the previous one
    save_lesson(req.user_id, req.topic_id, lesson_data, is_remedial=True)

    # Update student_progress to record weak subtopics
    progress_doc_id = f"{req.user_id}_{req.topic_id}"
    progress = get_document("student_progress", progress_doc_id)
    if progress:
        from firebase_admin import firestore as fs
        from services.firebase_service import update_document
        update_document("student_progress", progress_doc_id, {
            "weak_areas":    req.weak_subtopics,
            "last_attempt_at": fs.SERVER_TIMESTAMP,
        })

    return {
        "source":          "generated",
        "lesson":          lesson_data,
        "weak_subtopics":  req.weak_subtopics,
        "message":         "Personalized remedial lesson generated for your weak areas."
    }


@router.get("/history/{user_id}/{topic_id}")
def get_lesson_history(user_id: str, topic_id: str):
    """
    Returns both the initial and latest remedial lesson for a user+topic.
    Used by the Topic screen to show lesson history.
    """

    initial_id  = f"{user_id}_{topic_id}_initial"
    remedial_id = f"{user_id}_{topic_id}_remedial"

    initial  = get_document("user_lessons", initial_id)
    remedial = get_document("user_lessons", remedial_id)

    return {
        "user_id":        user_id,
        "topic_id":       topic_id,
        "initial_lesson": initial.get("lesson") if initial else None,
        "remedial_lesson": remedial.get("lesson") if remedial else None,
        "has_remedial":   remedial is not None,
    }