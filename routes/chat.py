from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.firebase_service import get_document
from services.openai_service import chat_with_tutor
from firebase_admin import firestore
import uuid
from datetime import datetime

router = APIRouter()

db = firestore.client()


# ─── Helper: Get or Create Session ───────────────────────────────────────────

def get_or_create_session(user_id: str, session_id: str = None):
    """
    If session_id provided and exists, return it.
    If session_id provided but doesn't exist, create it with that ID.
    If no session_id, create a brand new session.
    """
    sessions_ref = (
        db.collection("chat_history")
        .document(user_id)
        .collection("sessions")
    )

    if session_id:
        session_doc = sessions_ref.document(session_id).get()
        if session_doc.exists:
            return session_id
        # Session ID provided but doesn't exist — create it
        sessions_ref.document(session_id).set({
            "title":           "New Chat",
            "created_at":      firestore.SERVER_TIMESTAMP,
            "last_message_at": firestore.SERVER_TIMESTAMP,
            "message_count":   0,
        })
        return session_id
    else:
        # Create a brand new session
        new_session_ref = sessions_ref.document()
        new_session_ref.set({
            "title":           "New Chat",
            "created_at":      firestore.SERVER_TIMESTAMP,
            "last_message_at": firestore.SERVER_TIMESTAMP,
            "message_count":   0,
        })
        return new_session_ref.id


def update_session_metadata(
    user_id: str,
    session_id: str,
    first_message: str | None,
    message_count: int
):
    session_ref = (
        db.collection("chat_history")
        .document(user_id)
        .collection("sessions")
        .document(session_id)
    )

    update_data = {
        "last_message_at": firestore.SERVER_TIMESTAMP,
        "message_count":   message_count,
    }

    # Only set title from the very first message
    if first_message is not None:
        title = first_message[:40] + (
            "..." if len(first_message) > 40 else ""
        )
        update_data["title"] = title

    session_ref.update(update_data)


# ─── POST /chat/message ───────────────────────────────────────────────────────

@router.post("/message", response_model=ChatResponse)
def send_message(req: ChatRequest):

    # Verify user exists
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create session
    session_id = get_or_create_session(req.user_id, getattr(req, "session_id", None))

    # Get AI response
    response_text = chat_with_tutor(
        message       = req.message,
        history       = [m.dict() for m in req.history],
        topic_context = req.topic_context,
    )

    # Reference to this session's messages
    messages_ref = (
        db.collection("chat_history")
        .document(req.user_id)
        .collection("sessions")
        .document(session_id)
        .collection("messages")
    )

    # Count existing messages to update session metadata
    existing_count = len(list(messages_ref.stream()))

    # Save user message
    user_message_id = str(uuid.uuid4())
    messages_ref.document(user_message_id).set({
        "role":          "user",
        "content":       req.message,
        "topic_context": req.topic_context,
        "timestamp":     firestore.SERVER_TIMESTAMP,
    })

    # Save assistant response
    assistant_message_id = str(uuid.uuid4())
    messages_ref.document(assistant_message_id).set({
        "role":          "assistant",
        "content":       response_text,
        "topic_context": req.topic_context,
        "timestamp":     firestore.SERVER_TIMESTAMP,
    })

    # Only update title from the first message
    # existing_count is 0 before any messages are saved, so first message = count of 0
    update_session_metadata(
        req.user_id,
        session_id,
        req.message if existing_count == 0 else None,
        existing_count + 2,
    )

    # Also save to old flat path for backward compatibility
    old_ref = (
        db.collection("chat_history")
        .document(req.user_id)
        .collection("messages")
    )
    old_ref.document(user_message_id).set({
        "role":          "user",
        "content":       req.message,
        "topic_context": req.topic_context,
        "session_id":    session_id,
        "timestamp":     firestore.SERVER_TIMESTAMP,
    })
    old_ref.document(assistant_message_id).set({
        "role":          "assistant",
        "content":       response_text,
        "topic_context": req.topic_context,
        "session_id":    session_id,
        "timestamp":     firestore.SERVER_TIMESTAMP,
    })

    return ChatResponse(
        response   = response_text,
        message_id = assistant_message_id,
        session_id = session_id,
    )


# ─── GET /chat/history/{user_id} ─────────────────────────────────────────────

@router.get("/history/{user_id}")
def get_chat_history(user_id: str, session_id: str = None, limit: int = 50):

    # Verify user exists
    user = get_document("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if session_id:
        # Fetch messages from specific session
        messages_ref = (
            db.collection("chat_history")
            .document(user_id)
            .collection("sessions")
            .document(session_id)
            .collection("messages")
            .order_by("timestamp")
            .limit(limit)
        )
    else:
        # Fallback: fetch from old flat messages path
        messages_ref = (
            db.collection("chat_history")
            .document(user_id)
            .collection("messages")
            .order_by("timestamp")
            .limit(limit)
        )

    docs = messages_ref.stream()
    messages = []

    for doc in docs:
        data = doc.to_dict()
        messages.append({
            "message_id":    doc.id,
            "role":          data.get("role"),
            "content":       data.get("content"),
            "topic_context": data.get("topic_context"),
            "session_id":    data.get("session_id", session_id),
            "timestamp":     str(data.get("timestamp", "")),
        })

    return {"user_id": user_id, "messages": messages, "session_id": session_id}


# ─── GET /chat/sessions/{user_id} ────────────────────────────────────────────

@router.get("/sessions/{user_id}")
def get_chat_sessions(user_id: str):

    user = get_document("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions_ref = (
        db.collection("chat_history")
        .document(user_id)
        .collection("sessions")
        .order_by("last_message_at", direction=firestore.Query.DESCENDING)
        .limit(20)
    )

    docs = sessions_ref.stream()
    sessions = []

    for doc in docs:
        data = doc.to_dict()
        sessions.append({
            "session_id":      doc.id,
            "title":           data.get("title", "Chat Session"),
            "message_count":   data.get("message_count", 0),
            "created_at":      str(data.get("created_at", "")),
            "last_message_at": str(data.get("last_message_at", "")),
        })

    return {"user_id": user_id, "sessions": sessions}


# ─── POST /chat/sessions/{user_id} ───────────────────────────────────────────

@router.post("/sessions/{user_id}")
def create_chat_session(user_id: str):

    user = get_document("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_session_id = get_or_create_session(user_id, None)

    return {
        "user_id":    user_id,
        "session_id": new_session_id,
        "title":      "New Chat",
    }