import json
import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore

# CONFIGURATION

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
EXTRACTED_JSON_PATH  = "seed/curriculum_extracted.json"

# FIREBASE INIT

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# UPLOAD LOGIC
def upload_curriculum(db, data: dict):
    course_code = data["course_code"]
    course_title = data["course_title"]

    print(f"\n🚀 Starting upload for: {course_title} ({course_code})")
    print("="*60)

    # Create or update the course document
    print(f"\n📘 Writing course document...")
    course_ref = db.collection("courses").document()
    course_id = course_ref.id

    course_ref.set({
        "title":      course_title,
        "course_code": course_code,
        "description": f"Core undergraduate course covering {course_title}",
        "faculty":    "Science and Technology",
        "year_level": 1,
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    print(f"   ✅ Course created — ID: {course_id}")

    # Upload each topic
    topic_id_map = {}  # Maps topic_index → Firestore doc ID

    print(f"\n📚 Writing topics and curriculum guides...")

    for topic in data["topics"]:
        # Create topic document
        topic_ref = db.collection("topics").document()
        topic_id  = topic_ref.id
        topic_id_map[topic["topic_index"]] = topic_id

        # Resolve prerequisite topic ID
        prereq_index = topic["prerequisite_topic_index"]
        prereq_id    = topic_id_map.get(prereq_index) if prereq_index else None

        topic_ref.set({
            "course_id":              course_id,
            "title":                  topic["title"],
            "order_index":            topic["topic_index"],
            "prerequisite_topic_id":  prereq_id,
            "is_locked_by_default":   topic["topic_index"] != 1,
            "created_at":             firestore.SERVER_TIMESTAMP,
        })
        print(f"\n   ✅ Topic {topic['topic_index']}: {topic['title']}")
        print(f"      Firestore ID : {topic_id}")
        print(f"      Prerequisite : {prereq_id if prereq_id else 'None (first topic)'}")
        print(f"      Locked       : {topic['topic_index'] != 1}")

        # Create curriculum_guide document for this topic
        guide_ref = db.collection("curriculum_guides").document(topic_id)

        # Build subtopics array for Firestore
        subtopics_for_firestore = [
            {
                "title":          sub["title"],
                "key_content":    sub["extracted_text"],
                "source_pages":   sub["pages"],
            }
            for sub in topic["subtopics"]
        ]

        guide_ref.set({
            "topic_id":           topic_id,
            "course_id":          course_id,
            "topic_title":        topic["title"],
            "full_topic_text":    topic["full_topic_text"],
            "subtopics":          subtopics_for_firestore,
            "last_updated":       firestore.SERVER_TIMESTAMP,
        })
        print(f"      📖 Curriculum guide written — {len(subtopics_for_firestore)} subtopics")

    # Print summary
    print("\n" + "="*60)
    print("✅ UPLOAD COMPLETE")
    print("="*60)
    print(f"  Course ID : {course_id}")
    print(f"  Topics    : {len(data['topics'])} uploaded")
    print(f"  Guides    : {len(data['topics'])} curriculum guides created")
    print("\n📌 IMPORTANT — Save these IDs, you'll need them:")
    print(f"  Course ID → {course_id}")
    for index, tid in topic_id_map.items():
        label = data["topics"][index - 1]["title"]
        print(f"  Topic {index} ID → {tid}  ({label})")

    print("\n📌 Next step: Run python seed/seed_question_bank.py")

    return course_id, topic_id_map


# SAFETY CHECK — prevent accidental re-runs

def check_existing_course(db, course_code: str) -> bool:
    existing = db.collection("courses")\
                 .where("course_code", "==", course_code)\
                 .limit(1)\
                 .stream()
    return any(True for _ in existing)


# MAIN

if __name__ == "__main__":
    # Load extracted JSON
    if not os.path.exists(EXTRACTED_JSON_PATH):
        print(f"❌ File not found: {EXTRACTED_JSON_PATH}")
        print("   Run python seed/extract_curriculum.py first")
        sys.exit(1)

    with open(EXTRACTED_JSON_PATH, "r", encoding="utf-8") as f:
        curriculum_data = json.load(f)

    # Init Firebase
    db = init_firebase()

    # Safety check — don't upload twice
    if check_existing_course(db, curriculum_data["course_code"]):
        print(f"\n⚠️  Course '{curriculum_data['course_code']}' already exists in Firestore.")
        print("   To re-upload, manually delete the existing course/topic/guide documents first.")
        print("   Aborting to prevent duplicates.")
        sys.exit(0)

    # Run upload
    course_id, topic_id_map = upload_curriculum(db, curriculum_data)