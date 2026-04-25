import firebase_admin
from firebase_admin import credentials, firestore, auth
import sys

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"


def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def delete_collection(db, collection_ref, batch_size=100):
    """Delete all documents in a collection in batches."""
    deleted = 0
    while True:
        docs = list(collection_ref.limit(batch_size).stream())
        if not docs:
            break
        batch = db.batch()
        for doc in docs:
            batch.delete(doc.reference)
        batch.commit()
        deleted += len(docs)
    return deleted


def delete_subcollections_for_user(db, user_id):
    """Delete all subcollections under chat_history/{userId}."""
    chat_ref = db.collection("chat_history").document(user_id)

    # Delete sessions and their messages
    sessions = list(chat_ref.collection("sessions").stream())
    for session in sessions:
        messages = list(
            chat_ref.collection("sessions")
            .document(session.id)
            .collection("messages")
            .stream()
        )
        for msg in messages:
            msg.reference.delete()
        session.reference.delete()

    # Delete old flat messages
    old_messages = list(chat_ref.collection("messages").stream())
    for msg in old_messages:
        msg.reference.delete()

    # Delete the chat_history user document itself
    chat_ref.delete()


def cleanup_all_user_data(db):
    print("\n🧹 USER DATA CLEANUP SCRIPT")
    print("=" * 60)
    print("This will permanently delete ALL data from:")
    print("  • users (Firestore documents)")
    print("  • student_progress")
    print("  • user_lessons")
    print("  • quiz_sessions")
    print("  • chat_history (all sessions and messages)")
    print("  • user_badges")
    print("  • Firebase Authentication accounts")
    print("\nThe following will NOT be touched:")
    print("  • courses")
    print("  • topics")
    print("  • curriculum_guides")
    print("  • question_bank")
    print("  • badges")
    print("=" * 60)

    confirm = input("\nType 'CLEANUP' to confirm: ")
    if confirm != "CLEANUP":
        print("❌ Cancelled. Nothing was deleted.")
        sys.exit(0)

    print("\n🗑️  Starting cleanup...\n")
    total_deleted = 0

    # ── Step 1: Get all user IDs from Firestore ──────────────────────────
    print("📋 Fetching all user IDs from Firestore...")
    users_ref = db.collection("users")
    user_docs = list(users_ref.stream())
    user_ids = [doc.id for doc in user_docs]
    print(f"   Found {len(user_ids)} users\n")

    # ── Step 2: Delete chat_history subcollections per user ──────────────
    print("💬 Deleting chat history (sessions + messages)...")
    chat_deleted = 0
    for uid in user_ids:
        try:
            delete_subcollections_for_user(db, uid)
            chat_deleted += 1
        except Exception as e:
            print(f"   ⚠️  Failed for user {uid[:8]}...: {e}")
    print(f"   ✅ Cleared chat history for {chat_deleted} users\n")

    # ── Step 3: Delete top-level collections ─────────────────────────────
    collections_to_delete = [
        ("users",            "users"),
        ("student_progress", "student_progress"),
        ("user_lessons",     "user_lessons"),
        ("quiz_sessions",    "quiz_sessions"),
        ("user_badges",      "user_badges"),
    ]

    for label, col_name in collections_to_delete:
        print(f"🗑️  Deleting {label}...")
        count = delete_collection(db, db.collection(col_name))
        print(f"   ✅ {count} documents deleted\n")
        total_deleted += count

    # ── Step 4: Delete all Firebase Auth accounts ─────────────────────────
    print("🔐 Deleting Firebase Authentication accounts...")
    auth_deleted = 0
    auth_errors  = 0

    try:
        page = auth.list_users()
        while page:
            uids_to_delete = [user.uid for user in page.users]
            if uids_to_delete:
                result = auth.delete_users(uids_to_delete)
                auth_deleted += result.success_count
                auth_errors  += result.failure_count
                if result.failure_count > 0:
                    for err in result.errors:
                        print(f"   ⚠️  Failed to delete auth user: {err.reason}")
            if not page.has_next_page:
                break
            page = page.get_next_page()
    except Exception as e:
        print(f"   ⚠️  Auth deletion error: {e}")

    print(f"   ✅ {auth_deleted} auth accounts deleted")
    if auth_errors > 0:
        print(f"   ⚠️  {auth_errors} auth accounts failed to delete\n")

    # ── Summary ───────────────────────────────────────────────────────────
    print("=" * 60)
    print(f"✅ CLEANUP COMPLETE")
    print(f"   Firestore documents deleted : {total_deleted}")
    print(f"   Auth accounts deleted       : {auth_deleted}")
    print("=" * 60)
    print("\n📌 The following data was preserved:")
    print("   • courses")
    print("   • topics")
    print("   • curriculum_guides")
    print("   • question_bank")
    print("   • badges")
    print("\n✅ You can now create a fresh user for integration testing.")


if __name__ == "__main__":
    db = init_firebase()
    cleanup_all_user_data(db)