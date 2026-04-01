import json
import os
import sys
import time
import firebase_admin
from firebase_admin import credentials, firestore
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY")

COURSE_ID = "QhVX2kifeGLeN9Q1uJA7"

TOPICS = [
    {
        "topic_id":  "ycGFsUGZvO1XLCoCCQzg",
        "title":     "Introduction to Data Structures & Primitive Types",
        "subtopics": [
            "What are Data Structures and Why They Matter",
            "Primitive Types in C++",
            "Arrays in C++",
            "Records and Structs in C++",
        ]
    },
    {
        "topic_id":  "fVsptlyd8jXsSUdMr03V",
        "title":     "Strings & String Processing",
        "subtopics": [
            "Introduction to Strings in C++",
            "String Operations and Methods",
            "String Processing Techniques",
            "String Algorithms",
        ]
    },
    {
        "topic_id":  "eeq1aDo92ViFVa3JkwW3",
        "title":     "Memory, Stacks & Queues",
        "subtopics": [
            "Data Representation in Memory",
            "Stack and Heap Allocation",
            "Stack Data Structure",
            "Queue Data Structure",
            "Implementation Strategies for Stacks and Queues",
        ]
    },
    {
        "topic_id":  "sUbDh6txVZz2a4ee7Ggw",
        "title":     "Trees",
        "subtopics": [
            "Introduction to Trees",
            "Binary Trees and Binary Search Trees",
            "Tree Traversal",
            "Implementation Strategies for Trees",
        ]
    },
    {
        "topic_id":  "BeW7nroHcqe8CuCK4kna",
        "title":     "Pointers, References & Linked Structures",
        "subtopics": [
            "Pointers in C++",
            "References in C++",
            "Run-time Storage Management",
            "Linked Lists",
            "Linked List Operations",
        ]
    },
    {
        "topic_id":  "epUQhQBC23aCPc3Vj5ST",
        "title":     "Algorithms — Searching & Sorting",
        "subtopics": [
            "Searching Algorithms",
            "Bubble Sort",
            "Selection Sort and Insertion Sort",
            "Algorithm Analysis and Complexity",
        ]
    },
]

QUESTIONS_PER_DIFFICULTY = 15


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


def fetch_curriculum_guide(db, topic_id):
    doc = db.collection("curriculum_guides").document(topic_id).get()
    if not doc.exists:
        return ""
    data  = doc.to_dict()
    lines = [f"Topic: {data.get('topic_title', '')}"]
    for sub in data.get("subtopics", []):
        lines.append(f"\nSubtopic: {sub['title']}")
        lines.append(sub.get("key_content", ""))
    return "\n".join(lines)


def generate_questions(client, topic_title, subtopics, difficulty, curriculum_context, count):
    subtopic_list = "\n".join(f"- {s}" for s in subtopics)

    if difficulty == "easy":
        difficulty_guidance = """Focus on basic recall, definitions, and conceptual understanding.
Include simple C++ syntax questions and straightforward concept identification.
Mix: 10 multiple choice, 5 typed (short answer or simple code writing)."""
    else:
        difficulty_guidance = """Focus on application, algorithm tracing, code analysis and writing.
Include:
- Questions with C++ code snippets where students trace output or find errors
- Lab-style typed questions where students write C++ functions or implement algorithms
- Algorithm complexity analysis questions
- Questions requiring students to compare implementations
Mix: 8 multiple choice, 7 typed (code writing and algorithm tracing)."""

    prompt = f"""You are a Data Structures lecturer creating exam questions for
undergraduate Computer Science students studying CSC301 at a Nigerian university.
The course uses C++ as its programming language.

TOPIC: {topic_title}
DIFFICULTY: {difficulty.upper()}
SUBTOPICS TO COVER:
{subtopic_list}

CURRICULUM REFERENCE:
{curriculum_context}

INSTRUCTIONS:
{difficulty_guidance}

IMPORTANT FOR TYPED QUESTIONS:
- For lab-style typed questions, ask students to write actual C++ code
- Example: "Write a C++ function to push an element onto a stack implemented using an array"
- The correct_answer should contain a model C++ solution or clear algorithm steps
- Explanations should explain why the solution works

IMPORTANT FOR ALL QUESTIONS:
- Every subtopic must have at least 1 question
- Questions must be clearly worded and relevant to C++ and Data Structures
- Use correct C++ syntax in all code examples
- Explanations must be thorough and educational

Respond ONLY with a valid JSON array. No preamble, no markdown.

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
        max_tokens=5000,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def save_questions_to_firestore(db, questions, topic_id, course_id, difficulty):
    saved       = 0
    batch       = db.batch()
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
        saved       += 1
        batch_count += 1

        if batch_count == 499:
            batch.commit()
            batch       = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()

    return saved


if __name__ == "__main__":
    if COURSE_ID == "FILL_IN_AFTER_RUNNING_ADD_CSC301" or not TOPICS:
        print("❌ Please fill in COURSE_ID and TOPICS before running this script.")
        print("   Run python seed/add_csc301.py first to get the IDs.")
        sys.exit(1)

    db     = init_firebase()
    client = init_openai()

    total_saved  = 0
    difficulties = ["easy", "hard"]

    print("\n🌱 QUESTION BANK SEEDING — Data Structures (CSC301)")
    print("="*60)
    print(f"Topics: {len(TOPICS)}")
    print(f"Questions per difficulty: {QUESTIONS_PER_DIFFICULTY}")
    print(f"Target: {len(TOPICS) * 2 * QUESTIONS_PER_DIFFICULTY} questions")
    print("="*60)

    for topic in TOPICS:
        topic_id    = topic["topic_id"]
        topic_title = topic["title"]

        print(f"\n📚 {topic_title}")

        curriculum_context = fetch_curriculum_guide(db, topic_id)
        if not curriculum_context:
            print(f"   ⚠️  No curriculum guide — skipping")
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

                mc_count = sum(1 for q in questions if q.get("question_type") == "multiple_choice")
                t_count  = sum(1 for q in questions if q.get("question_type") == "typed")
                print(f"   📊 Mix: {mc_count} multiple choice, {t_count} typed")

                if questions:
                    first = questions[0]
                    print(f"   📝 Sample: [{first['question_type'].upper()}] "
                          f"{first['question_text'][:70]}...")

                saved = save_questions_to_firestore(
                    db, questions, topic_id, COURSE_ID, difficulty
                )
                total_saved += saved
                print(f"   💾 Saved {saved} questions")

                time.sleep(2)

            except json.JSONDecodeError as e:
                print(f"   ❌ JSON error: {e}")
                continue
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue

    print("\n" + "="*60)
    print(f"✅ SEEDING COMPLETE — {total_saved} total questions saved")
    print("="*60)
