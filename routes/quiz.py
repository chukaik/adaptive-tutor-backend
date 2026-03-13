from fastapi import APIRouter, HTTPException
from models.schemas import (
    QuizFetchRequest, QuizFetchResponse, QuestionOut,
    QuizSubmitRequest, QuizSubmitResponse, QuestionResult,
    HintRequest, HintResponse, PersonalizedQuizRequest,
    NextAction, MasteryLevel, Difficulty
)
from services.firebase_service import (
    get_document, set_document, update_document,
    query_collection, add_document
)
from services.openai_service import (
    get_hint, get_explanation, grade_typed_answer,
    generate_personalized_questions
)
from services.adaptive_engine import evaluate, compute_score
from firebase_admin import firestore
import random

router = APIRouter()


# Fetch curriculum guide context

def fetch_curriculum_context(topic_id: str) -> str:
    doc = get_document("curriculum_guides", topic_id)
    if not doc:
        return ""
    lines = [f"Topic: {doc.get('topic_title', '')}"]
    for sub in doc.get("subtopics", []):
        lines.append(f"\nSubtopic: {sub['title']}")
        lines.append(sub.get("key_content", ""))
    return "\n".join(lines)


# QUIZ FETCH

@router.post("/fetch", response_model=QuizFetchResponse)
def fetch_quiz(req: QuizFetchRequest):

    # Verify user and topic exist
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    topic = get_document("topics", req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Verify topic is unlocked for this user
    progress_doc_id = f"{req.user_id}_{req.topic_id}"
    progress = get_document("student_progress", progress_doc_id)

    if not progress or not progress.get("is_unlocked", False):
        raise HTTPException(
            status_code=403,
            detail="This topic is locked. Complete the prerequisite topic first."
        )

    # Verify correct difficulty is being requested
    difficulty_unlocked = progress.get("difficulty_unlocked", "easy")
    if req.difficulty.value == "hard" and difficulty_unlocked == "easy":
        raise HTTPException(
            status_code=403,
            detail="Complete the easy quiz first before attempting the hard quiz."
        )

    # Fetch questions from question bank
    all_questions = query_collection("question_bank", [
        ("topic_id",   "==", req.topic_id),
        ("difficulty", "==", req.difficulty.value),
    ])

    if not all_questions:
        raise HTTPException(
            status_code=404,
            detail="No questions found for this topic and difficulty."
        )

    # Select 10 random questions
    selected = random.sample(all_questions, min(10, len(all_questions)))

    # Build question output (never expose correct_answer)
    questions_out = []
    question_ids  = []

    for q in selected:
        questions_out.append(QuestionOut(
            question_id   = q["id"],
            question_type = q.get("question_type"),
            question_text = q.get("question_text"),
            subtopic      = q.get("subtopic", ""),
            options       = q.get("options"),
        ))
        question_ids.append(q["id"])

    # Create quiz session in Firestore
    session_id = add_document("quiz_sessions", {
        "user_id":          req.user_id,
        "topic_id":         req.topic_id,
        "difficulty":       req.difficulty.value,
        "session_type":     req.session_type.value,
        "questions":        question_ids,
        "answers_submitted": [],
        "score":            0.0,
        "passed":           False,
        "weak_question_ids": [],
        "time_taken_seconds": 0,
        "timestamp":        firestore.SERVER_TIMESTAMP,
    })

    return QuizFetchResponse(
        session_id = session_id,
        topic_id   = req.topic_id,
        difficulty = req.difficulty.value,
        questions  = questions_out,
    )


# QUIZ SUBMIT & GRADE

@router.post("/submit", response_model=QuizSubmitResponse)
def submit_quiz(req: QuizSubmitRequest):

    # Verify session exists
    session = get_document("quiz_sessions", req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found")

    # Verify user and topic
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    topic = get_document("topics", req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Grade each answer
    results          = []
    correct_count    = 0
    weak_question_ids = []
    weak_subtopics   = set()
    answers_submitted = []

    for answer in req.answers:
        # Fetch the question document to get correct answer
        question_doc = get_document("question_bank", answer.question_id)

        if not question_doc:
            continue

        correct_answer = question_doc.get("correct_answer", "")
        question_text  = question_doc.get("question_text", "")
        question_type  = question_doc.get("question_type", "multiple_choice")
        subtopic       = question_doc.get("subtopic", "")
        explanation    = question_doc.get("explanation", "")
        ai_reasoning   = None

        # Grade based on question type
        if answer.question_type.value == "multiple_choice":
            # Direct comparison — strip whitespace for safety
            is_correct = (
                answer.student_answer.strip().lower() ==
                correct_answer.strip().lower()
            )
        else:
            # Typed answer (use AI semantic grading)
            grading_result = grade_typed_answer(
                question_text  = question_text,
                correct_answer = correct_answer,
                student_answer = answer.student_answer,
            )
            is_correct   = grading_result.get("is_correct", False)
            ai_reasoning = grading_result.get("reasoning", "")

        if is_correct:
            correct_count += 1
            # Update question usage stats
            update_document("question_bank", answer.question_id, {
                "times_used":    firestore.Increment(1),
                "times_correct": firestore.Increment(1),
            })
        else:
            weak_question_ids.append(answer.question_id)
            weak_subtopics.add(subtopic)
            update_document("question_bank", answer.question_id, {
                "times_used": firestore.Increment(1),
            })

        answers_submitted.append({
            "question_id":       answer.question_id,
            "question_type":     answer.question_type.value,
            "student_answer":    answer.student_answer,
            "is_correct":        is_correct,
            "ai_grading_reasoning": ai_reasoning,
        })

        results.append(QuestionResult(
            question_id    = answer.question_id,
            question_text  = question_text,
            question_type  = answer.question_type,
            student_answer = answer.student_answer,
            correct_answer = correct_answer,
            is_correct     = is_correct,
            explanation    = explanation,
            subtopic       = subtopic,
            ai_reasoning   = ai_reasoning,
        ))

    # Calculate score
    total    = len(req.answers)
    score    = compute_score(correct_count, total)

    # Run adaptive engine
    # Check if there is a next topic
    all_topics = query_collection("topics", [
        ("course_id", "==", topic.get("course_id", ""))
    ])
    all_topics.sort(key=lambda t: t.get("order_index", 0))
    current_order = topic.get("order_index", 1)
    next_topic    = next(
        (t for t in all_topics if t.get("order_index", 0) == current_order + 1),
        None
    )

    adaptive_result = evaluate(
        score          = score,
        difficulty     = req.difficulty.value,
        has_next_topic = next_topic is not None,
    )

    next_action   = adaptive_result["next_action"]
    mastery_level = adaptive_result["mastery_level"]
    passed        = adaptive_result["passed"]
    message       = adaptive_result["message"]
    next_topic_id = None

    # Update student_progress
    progress_doc_id = f"{req.user_id}_{req.topic_id}"
    progress        = get_document("student_progress", progress_doc_id)
    current_attempts = progress.get("attempts", 0) if progress else 0

    progress_update = {
        "attempts":        current_attempts + 1,
        "mastery_level":   mastery_level.value,
        "accuracy":        score,
        "last_attempt_at": firestore.SERVER_TIMESTAMP,
        "weak_areas":      list(weak_subtopics),
    }

    if next_action == NextAction.increase_difficulty:
        progress_update["difficulty_unlocked"]  = "hard"
        progress_update["easy_quiz_best_score"] = max(
            score, progress.get("easy_quiz_best_score", 0.0) if progress else 0.0
        )

    elif next_action == NextAction.unlock_next_topic:
        progress_update["difficulty_unlocked"]  = "completed"
        progress_update["hard_quiz_best_score"] = max(
            score, progress.get("hard_quiz_best_score", 0.0) if progress else 0.0
        )
        # Unlock the next topic
        if next_topic:
            next_topic_id       = next_topic["id"]
            next_progress_id    = f"{req.user_id}_{next_topic_id}"
            next_progress       = get_document("student_progress", next_progress_id)
            if next_progress:
                update_document("student_progress", next_progress_id, {
                    "is_unlocked":   True,
                    "mastery_level": "low",
                })
            else:
                set_document("student_progress", next_progress_id, {
                    "user_id":              req.user_id,
                    "topic_id":             next_topic_id,
                    "course_id":            topic.get("course_id", ""),
                    "mastery_level":        "low",
                    "easy_quiz_best_score": 0.0,
                    "hard_quiz_best_score": 0.0,
                    "attempts":             0,
                    "accuracy":             0.0,
                    "weak_areas":           [],
                    "difficulty_unlocked":  "easy",
                    "is_unlocked":          True,
                    "last_attempt_at":      firestore.SERVER_TIMESTAMP,
                })

    elif next_action == NextAction.repeat_concept:
        # Update best score only if better than current
        if req.difficulty.value == "easy":
            current_best = progress.get("easy_quiz_best_score", 0.0) if progress else 0.0
            progress_update["easy_quiz_best_score"] = max(score, current_best)
        else:
            current_best = progress.get("hard_quiz_best_score", 0.0) if progress else 0.0
            progress_update["hard_quiz_best_score"] = max(score, current_best)

    update_document("student_progress", progress_doc_id, progress_update)

    # Update quiz session with results
    update_document("quiz_sessions", req.session_id, {
        "answers_submitted":  answers_submitted,
        "score":              score,
        "passed":             passed,
        "weak_question_ids":  weak_question_ids,
        "time_taken_seconds": req.time_taken_seconds,
    })

    return QuizSubmitResponse(
        session_id      = req.session_id,
        score           = score,
        passed          = passed,
        total_questions = total,
        correct_count   = correct_count,
        next_action     = next_action,
        next_topic_id   = next_topic_id,
        mastery_level   = mastery_level,
        message         = message,
        results         = results,
    )


# HINT

@router.post("/hint", response_model=HintResponse)
def request_hint(req: HintRequest):
    hint = get_hint(
        question_text = req.question_text,
        topic         = req.topic,
        difficulty    = req.difficulty,
    )
    return HintResponse(hint=hint)


# GENERATE PERSONALIZED QUIZ

@router.post("/generate-personalized", response_model=QuizFetchResponse)
def generate_personalized_quiz(req: PersonalizedQuizRequest):

    # Verify user and topic
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    topic = get_document("topics", req.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get curriculum context for this topic
    curriculum_context = fetch_curriculum_context(req.topic_id)

    # Generate personalized questions via OpenAI
    generated = generate_personalized_questions(
        topic_title            = topic.get("title", ""),
        weak_subtopics         = req.weak_subtopics,
        difficulty             = req.difficulty.value,
        curriculum_context     = curriculum_context,
        previous_question_ids  = req.previous_question_ids,
        count                  = 10,
    )

    # Save generated questions to question_bank
    question_ids  = []
    questions_out = []

    for q in generated:
        new_question_id = add_document("question_bank", {
            "topic_id":      req.topic_id,
            "course_id":     topic.get("course_id", ""),
            "difficulty":    req.difficulty.value,
            "question_type": q.get("question_type"),
            "subtopic":      q.get("subtopic", ""),
            "question_text": q.get("question_text"),
            "options":       q.get("options"),
            "correct_answer": q.get("correct_answer"),
            "explanation":   q.get("explanation"),
            "source":        "ai_generated",
            "times_used":    0,
            "times_correct": 0,
            "created_at":    firestore.SERVER_TIMESTAMP,
        })

        question_ids.append(new_question_id)
        questions_out.append(QuestionOut(
            question_id   = new_question_id,
            question_type = q.get("question_type"),
            question_text = q.get("question_text"),
            subtopic      = q.get("subtopic", ""),
            options       = q.get("options"),
        ))

    # Create quiz session
    session_id = add_document("quiz_sessions", {
        "user_id":           req.user_id,
        "topic_id":          req.topic_id,
        "difficulty":        req.difficulty.value,
        "session_type":      "personalized",
        "questions":         question_ids,
        "answers_submitted": [],
        "score":             0.0,
        "passed":            False,
        "weak_question_ids": [],
        "time_taken_seconds": 0,
        "timestamp":         firestore.SERVER_TIMESTAMP,
    })

    return QuizFetchResponse(
        session_id = session_id,
        topic_id   = req.topic_id,
        difficulty = req.difficulty.value,
        questions  = questions_out,
    )