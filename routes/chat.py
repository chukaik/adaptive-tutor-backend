from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.firebase_service import get_document, add_document
from services.openai_service import chat_with_tutor
from firebase_admin import firestore
import uuid

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
def send_message(req: ChatRequest):

    # Verify user exists
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get AI response
    response_text = chat_with_tutor(
        message       = req.message,
        history       = [m.dict() for m in req.history],
        topic_context = req.topic_context,
    )

    # Save user message to Firestore
    user_message_id = str(uuid.uuid4())
    db_user_msg_ref = (
        firestore.client()
        .collection("chat_history")
        .document(req.user_id)
        .collection("messages")
        .document(user_message_id)
    )
    db_user_msg_ref.set({
        "role":          "user",
        "content":       req.message,
        "topic_context": req.topic_context,
        "timestamp":     firestore.SERVER_TIMESTAMP,
    })

    # Save assistant response to Firestore
    assistant_message_id = str(uuid.uuid4())
    db_assistant_msg_ref = (
        firestore.client()
        .collection("chat_history")
        .document(req.user_id)
        .collection("messages")
        .document(assistant_message_id)
    )
    db_assistant_msg_ref.set({
        "role":          "assistant",
        "content":       response_text,
        "topic_context": req.topic_context,
        "timestamp":     firestore.SERVER_TIMESTAMP,
    })

    return ChatResponse(
        response   = response_text,
        message_id = assistant_message_id,
    )


@router.get("/history/{user_id}")
def get_chat_history(user_id: str, limit: int = 50):

    # Verify user exists
    user = get_document("users", req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch messages from Firestore subcollection
    messages_ref = (
        firestore.client()
        .collection("chat_history")
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
            "timestamp":     str(data.get("timestamp", "")),
        })

    return {"user_id": user_id, "messages": messages}