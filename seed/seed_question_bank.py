import json
import os
import sys
import time
import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# CONFIGURATION

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")

COURSE_ID  = "PXjKoQ1eRONaMfEO6QCX"

TOPICS = [
    {
        "topic_id":    "Q4cy6QzPuVnBRWZVkqkW",
        "title":       "Java Data Types & Variables",
        "subtopics":   [
            "Java Data Types Overview",
            "Primitive Data Types",
            "Non-Primitive Data Types",
            "Variables Overview",
            "Types of Variables",
        ]
    },
    {
        "topic_id":    "l4OWlXGn4fEcodnoYmKL",
        "title":       "Object-Oriented Programming (OOP) Concepts",
        "subtopics":   [
            "Introduction to Objects",
            "Classes",
            "The Four Pillars of OOP",
            "Access Modifiers",
            "Java Applications (Applets, Applications, Servlets)",
        ]
    },
    {
        "topic_id":    "kRoW8eu7DVfPVRqzstqt",
        "title":       "Java Packages",
        "subtopics":   [
            "Package Fundamentals",
            "Types of Packages",
            "Accessing Packages",
        ]
    },
    {
        "topic_id":    "iwUFrLEeiMzWdhsn7Zby",
        "title":       "Exception Handling",
        "subtopics":   [
            "Introduction to Exceptions",
            "Types of Exceptions",
            "Exception Hierarchy",
            "Handling Mechanisms",
        ]
    },
]

QUESTIONS_PER_DIFFICULTY = 15


# FIREBASE + OPENAI INIT

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def init_openai():
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not found in .env")
        sys.exit(1)
    return OpenAI(api_key=OPENAI_API_KEY)


# CURRICULUM GUIDE FETCHER

def fetch_curriculum_guide(db, topic_id: str) -> str:
    doc = db.collection("curriculum_guides").document(topic_id).get()
    if not doc.exists:
        return ""
    data = doc.to_dict()
    # Build a readable summary of the curriculum guide
    lines = [f"Topic: {data.get('topic_title', '')}"]
    for sub in data.get("subtopics", []):
        lines.append(f"\nSubtopic: {sub['title']}")
        lines.append(sub.get("key_content", ""))
    return "\n".join(lines)


# QUESTION GENERATION

def generate_questions(
    client: OpenAI,
    topic_title: str,
    subtopics: list,
    difficulty: str,
    curriculum_context: str,
    count: int
) -> list:

    subtopic_list = "\n".join(f"- {s}" for s in subtopics)
    difficulty_guidance = (
        "Focus on basic recall, definitions, and simple identification."
        if difficulty == "easy"
        else
        "Focus on application, code analysis, tracing, and deeper understanding. "
        "Include questions that require students to read short code snippets and "
        "determine outputs or identify errors."
    )

    prompt = f"""You are a Java programming lecturer creating exam questions for undergraduate students.

COURSE TOPIC: {topic_title}
DIFFICULTY: {difficulty.upper()}
SUBTOPICS TO COVER:
{subtopic_list}

CURRICULUM REFERENCE (base your questions on this content):
{curriculum_context}

DIFFICULTY GUIDANCE:
{difficulty_guidance}

TASK:
Generate exactly {count} questions about the topic above.
- Mix of question types: roughly 10 multiple choice and 5 typed (short answer)
- For multiple choice: provide exactly 4 options labeled A, B, C, D
- For typed: no options needed, just the question and correct answer
- Every subtopic must have at least 1 question
- Questions must be clearly worded and unambiguous
- Explanations must be educational and helpful

Respond ONLY with a valid JSON array. No preamble, no markdown, no extra text.
Use exactly this structure:

[
  {{
    "question_type": "multiple_choice",
    "question_text": "...",
    "subtopic": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_answer": "A. ...",
    "explanation": "..."
  }},
  {{
    "question_type": "typed",
    "question_text": "...",
    "subtopic": "...",
    "options": null,
    "correct_answer": "...",
    "explanation": "..."
  }}
]"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    questions = json.loads(raw)
    return questions


# FIRESTORE WRITER

def save_questions_to_firestore(
    db,
    questions: list,
    topic_id: str,
    course_id: str,
    difficulty: str
) -> int:
    saved = 0
    batch = db.batch()
    batch_count = 0

    for q in questions:
        ref = db.collection("question_bank").document()
        batch.set(ref, {
            "topic_id":       topic_id,
            "course_id":      course_id,
            "difficulty":     difficulty,
            "question_type":  q.get("question_type"),
            "subtopic":       q.get("subtopic", ""),
            "question_text":  q.get("question_text"),
            "options":        q.get("options"),
            "correct_answer": q.get("correct_answer"),
            "explanation":    q.get("explanation"),
            "source":         "seeded",
            "times_used":     0,
            "times_correct":  0,
            "created_at":     firestore.SERVER_TIMESTAMP,
        })
        saved += 1
        batch_count += 1

        # Firestore batch limit is 500 — commit and start new batch
        if batch_count == 499:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()

    return saved


# MAIN

if __name__ == "__main__":
    db     = init_firebase()
    client = init_openai()

    total_saved = 0
    difficulties = ["easy", "hard"]

    print("\n🌱 QUESTION BANK SEEDING — Computer Programming I")
    print("="*60)

    for topic in TOPICS:
        topic_id    = topic["topic_id"]
        topic_title = topic["title"]

        print(f"\n📚 Topic: {topic_title}")

        # Fetch curriculum guide from Firestore
        curriculum_context = fetch_curriculum_guide(db, topic_id)
        if not curriculum_context:
            print(f"   ⚠️  No curriculum guide found for topic {topic_id} — skipping")
            continue

        for difficulty in difficulties:
            print(f"\n   🎯 Generating {QUESTIONS_PER_DIFFICULTY} {difficulty.upper()} questions...")

            try:
                questions = generate_questions(
                    client=client,
                    topic_title=topic_title,
                    subtopics=topic["subtopics"],
                    difficulty=difficulty,
                    curriculum_context=curriculum_context,
                    count=QUESTIONS_PER_DIFFICULTY,
                )

                print(f"   ✅ Generated {len(questions)} questions")

                # Preview first question
                if questions:
                    first = questions[0]
                    print(f"   📝 Sample: [{first['question_type'].upper()}] "
                          f"{first['question_text'][:80]}...")

                # Save to Firestore
                saved = save_questions_to_firestore(
                    db, questions, topic_id, COURSE_ID, difficulty
                )
                total_saved += saved
                print(f"   💾 Saved {saved} questions to Firestore")

                # Pause between API calls to be safe
                time.sleep(2)

            except json.JSONDecodeError as e:
                print(f"   ❌ JSON parse error for {topic_title} {difficulty}: {e}")
                print("      Skipping this batch — you can re-run for failed topics")
                continue

            except Exception as e:
                print(f"   ❌ Error for {topic_title} {difficulty}: {e}")
                continue

    print("\n" + "="*60)
    print(f"✅ SEEDING COMPLETE — {total_saved} total questions saved to Firestore")
    print("="*60)
    print("\n📌 Next step: Go to Firebase console → question_bank collection")
    print("   Review the generated questions before proceeding to Phase 2")