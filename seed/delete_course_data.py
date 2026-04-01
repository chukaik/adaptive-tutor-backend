import firebase_admin
from firebase_admin import credentials, firestore
import sys

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def delete_collection(db, collection_name, batch_size=100):
    """Delete all documents in a collection in batches."""
    print(f"\n🗑️  Deleting collection: {collection_name}")
    col_ref = db.collection(collection_name)
    deleted  = 0

    while True:
        docs = col_ref.limit(batch_size).stream()
        doc_list = list(docs)

        if not doc_list:
            break

        batch = db.batch()
        for doc in doc_list:
            batch.delete(doc.reference)
        batch.commit()
        deleted += len(doc_list)
        print(f"   Deleted {deleted} documents so far...")

    print(f"   ✅ {collection_name} — {deleted} total documents deleted")
    return deleted


def delete_subcollections(db, collection_name, subcollection_name, batch_size=100):
    """Delete subcollections inside each document of a collection."""
    print(f"\n🗑️  Deleting subcollections: {collection_name}/*/{{subcollection_name}}")
    parent_docs = db.collection(collection_name).stream()
    total_deleted = 0

    for parent_doc in parent_docs:
        sub_ref = (
            db.collection(collection_name)
            .document(parent_doc.id)
            .collection(subcollection_name)
        )
        deleted = 0
        while True:
            docs = sub_ref.limit(batch_size).stream()
            doc_list = list(docs)
            if not doc_list:
                break
            batch = db.batch()
            for doc in doc_list:
                batch.delete(doc.reference)
            batch.commit()
            deleted += len(doc_list)

        if deleted > 0:
            print(f"   Deleted {deleted} messages from {parent_doc.id}")
        total_deleted += deleted

    print(f"   ✅ Total subcollection documents deleted: {total_deleted}")
    return total_deleted


if __name__ == "__main__":
    print("\n⚠️  COURSE DATA DELETION SCRIPT")
    print("="*60)
    print("This will permanently delete all documents from:")
    print("  • courses")
    print("  • topics")
    print("  • curriculum_guides")
    print("  • question_bank")
    print("  • student_progress")
    print("  • user_lessons")
    print("  • quiz_sessions")
    print("\nThe following will NOT be touched:")
    print("  • users")
    print("  • chat_history")
    print("  • badges")
    print("  • user_badges")
    print("="*60)

    confirm = input("\nType 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("❌ Cancelled. Nothing was deleted.")
        sys.exit(0)

    db = init_firebase()

    collections_to_delete = [
        "courses",
        "topics",
        "curriculum_guides",
        "question_bank",
        "student_progress",
        "user_lessons",
        "quiz_sessions",
    ]

    total = 0
    for col in collections_to_delete:
        total += delete_collection(db, col)

    print("\n" + "="*60)
    print(f"✅ DELETION COMPLETE — {total} total documents deleted")
    print("="*60)
    print("\n📌 Next steps:")
    print("   1. python seed/extract_curriculum.py")
    print("   2. python seed/upload_curriculum.py")
    print("   3. python seed/seed_question_bank.py")
