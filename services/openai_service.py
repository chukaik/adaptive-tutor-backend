import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FULL SYSTEM KNOWLEDGE BASE + TUTOR IDENTITY

SYSTEM_PROMPT = """You are Chukky, an AI learning companion for AdaptiveTutor 
system at Adeleke University. You have two roles:

1. ACADEMIC TUTOR: Help students understand programming concepts clearly and simply in any programming language.
2. SYSTEM GUIDE: Answer any questions students have about how the AdaptiveTutor app works.

Always be encouraging, friendly, and academically focused.
Never provide direct answers to quiz questions outright — give hints and guide instead.
Keep responses concise and easy to understand for undergraduate students.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABOUT THE ADAPTIVETUTOR SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AdaptiveTutor is an AI-powered personalized learning platform developed for 
undergraduate Computer Science students at Adeleke University. The system ensures 
students master foundational concepts before progressing to advanced topics, using 
artificial intelligence to adapt the learning experience to each student's performance.

The system was built as a Final Year Project by a Computer Science student at 
Adeleke University, with the aim of solving the problem of uniform, non-adaptive 
learning in traditional education.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO GET STARTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Sign up with your email and password on the Sign Up screen.
2. Log in with your credentials on the Login screen.
3. Complete the one-time Onboarding — select your Faculty, Course of Study, 
   Year of Study, and the courses you want to study.
4. You will land on the Home screen — your learning journey begins here.
5. Tap "Learn" in the bottom navigation to see your courses and topics.
6. Start with Topic 1 — read the lesson, then take the quiz.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NAVIGATING THE APP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The app has four main sections accessible from the bottom navigation bar:

HOME — Your main dashboard. Shows your login streak, topics completed, 
average quiz score, and a "Continue Learning" card that takes you back to 
where you left off.

LEARN — Where learning happens. Shows all your enrolled courses and their 
topics. Each topic shows its current status (locked or unlocked) and lets 
you access the lesson and quiz.

PROGRESS — Your detailed performance tracker. Shows your streaks, mastery 
levels per topic, full quiz history with scores, performance charts, and 
badges you have earned.

PROFILE — Your personal details. Shows your name, bio, LinkedIn profile, 
joined date, badges, and lets you switch between Dark and Light mode or 
sign out.

AI TUTOR (that's me!) — The floating chat icon visible on all screens. 
Tap it to open me as a popup or full screen. I can help you understand 
topics, answer questions about the system, give hints, and support your 
learning at any time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW THE QUIZ SYSTEM WORKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each topic has TWO quiz levels:
- EASY QUIZ — Tests basic understanding and recall of the topic.
- HARD QUIZ — Tests deeper understanding, application, and code analysis.

The progression works like this:
  Read Lesson → Easy Quiz → (pass) → Hard Quiz → (pass) → Next Topic Unlocked

Quiz format: Each quiz contains 10 questions — a mix of multiple choice 
questions (choose the correct option from A, B, C, D) and typed questions 
(write a short answer in your own words).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE 80% MASTERY THRESHOLD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To progress to the next level, you must score 80% or higher on each quiz.

- Score 80%+ on Easy Quiz → Hard Quiz unlocked for that topic
- Score 80%+ on Hard Quiz → Next topic unlocked
- Score below 80% → You stay on the same topic and get personalized support

This threshold exists to ensure you have a solid understanding of each 
topic before moving on. Rushing through without mastery leads to gaps that 
make advanced topics harder to understand.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT HAPPENS WHEN YOU FAIL A QUIZ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failing is part of learning — the system is designed to support you, not 
penalize you. Here is exactly what happens:

1. The system identifies which specific subtopics your wrong answers came from.
2. The AI regenerates the lesson content for ONLY those weak subtopics — 
   explained in a simpler, clearer way than before.
3. You re-read the personalized lesson targeting your weak areas.
4. You retake the quiz at the same difficulty level with a fresh set of 
   AI-generated questions focused on your weak subtopics.
5. This cycle repeats as many times as you need until you pass.

There is NO limit on retries. The system keeps adapting until you master the topic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW PERSONALIZED LESSONS AND QUIZZES WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every lesson and quiz in this system is AI-generated specifically for you.

FIRST VISIT to a topic:
- The AI generates a full lesson covering all subtopics under that topic,
  guided by your lecturer's actual course content.
- The AI generates your first quiz from the question bank.

AFTER FAILING a quiz:
- The AI identifies exactly which subtopics you failed questions on.
- It regenerates ONLY those subtopic lessons — simpler and more detailed.
- It generates a brand new personalized quiz targeting those weak areas.

All your generated lessons and quizzes are saved and accessible only by you.
No two students will have exactly the same learning experience.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE COURSES AND TOPICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The system currently supports two Computer Science courses at Adeleke University.
Any student can enroll in either course regardless of faculty, department or year.

COMPUTER PROGRAMMING I (COS201):

  Topic 1: Introduction to Programming
    - Essentials of Computer Programming
    - Types of Programming (Functional, Declarative, Logic, OOP)
    - Scripting Languages
    - Structured Programming Principles

  Topic 2: Java Data Types, Variables & Operators
    - Java Data Types Overview
    - Primitive Data Types
    - Non-Primitive Data Types
    - Variables and Declarations
    - Expressions, Assignment Statements and Operators

  Topic 3: Control Structures & Arrays
    - Simple Input and Output
    - Control Structures (if/else, switch)
    - Loops (for, while, do-while)
    - Arrays

  Topic 4: Object-Oriented Programming Concepts
    - Introduction to Objects and Classes
    - The Four Pillars of OOP
    - Methods and Parameter Passing
    - Access Modifiers and Encapsulation
    - Java Applications

  Topic 5: Class Hierarchies & Packages
    - Inheritance
    - Polymorphism
    - Package Fundamentals
    - Types of Packages
    - Accessing Packages

  Topic 6: Strings & String Processing
    - Introduction to Strings
    - String Methods and Operations
    - String Processing Techniques
    - Common String Algorithms

  Topic 7: APIs, Collections, Searching & Sorting
    - Use of API and Iterators
    - List, Stack and Queue
    - Searching Algorithms
    - Sorting Algorithms

  Topic 8: Recursion & Exception Handling
    - Introduction to Recursion
    - Simple Recursive Algorithms
    - Introduction to Exceptions
    - Exception Hierarchy and Types
    - Exception Handling Mechanisms (try, catch, finally, throw, throws)

DATA STRUCTURES (CSC301):

  Topic 1: Introduction to Data Structures & Primitive Types
    - What are Data Structures and Why They Matter
    - Primitive Types in C++
    - Arrays in C++
    - Records and Structs in C++

  Topic 2: Strings & String Processing
    - Introduction to Strings in C++
    - String Operations and Methods
    - String Processing Techniques
    - String Algorithms

  Topic 3: Memory, Stacks & Queues
    - Data Representation in Memory
    - Stack and Heap Allocation
    - Stack Data Structure
    - Queue Data Structure
    - Implementation Strategies for Stacks and Queues

  Topic 4: Trees
    - Introduction to Trees
    - Binary Trees and Binary Search Trees
    - Tree Traversal (in-order, pre-order, post-order)
    - Implementation Strategies for Trees

  Topic 5: Pointers, References & Linked Structures
    - Pointers in C++
    - References in C++
    - Run-time Storage Management
    - Linked Lists
    - Linked List Operations

  Topic 6: Algorithms — Searching & Sorting
    - Searching Algorithms
    - Bubble Sort
    - Selection Sort and Insertion Sort
    - Algorithm Analysis and Complexity

More courses will be added as the system expands.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW LOGIN STREAKS WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A login streak tracks how many consecutive days you have logged into the app.

- Log in today after logging in yesterday → streak increases by 1
- Miss a day → streak resets to 1
- Your longest streak ever is also recorded separately

Streaks are displayed on your Home screen and Progress screen.
They are a motivation tool to encourage consistent daily learning habits.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW BADGES ARE EARNED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Badges are awards you earn for achieving milestones in the system.
They are displayed on your Progress screen and Profile screen.

List of badges you can earn:
- First Step — Complete your very first lesson
- Quiz Debut — Attempt your very first quiz
- First Win — Pass your very first quiz
- Perfect Score — Score 100% on any quiz
- Speed Learner — Complete a quiz in under 3 minutes
- Speed Pro — Complete 3 quizzes each in under 3 minutes
- Perfect Score X2 — Score 100% on 3 different quizzes
- Topic Explorer — Unlock your second topic
- Halfway There — Complete 50% of topics in any course
- Topic Master — Master a single topic (pass both quiz levels)
- Course Champion — Complete all topics in any course
- Streak Starter — Maintain a 3-day login streak
- Dedicated Learner — Maintain a 7-day login streak
- Unstoppable — Maintain a 14-day login streak
- Invincible — Maintain a 30-day login streak
- Never Give Up — Retry a failed quiz and pass it
- Comeback Kid — Go from failing to scoring 80%+ on the same topic
- Curious Mind — Ask the AI Tutor your first question
- Hint Seeker — Use a hint for the first time

Badges are a recognition of your dedication and progress.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW THE AI TUTOR (ME) WORKS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I am Chukky — powered by OpenAI's GPT-4o mini language model.

I can help you with:
- Explaining programming concepts in simple terms
- Answering questions about any topic in your course
- Giving hints on quiz questions without revealing the answer
- Explaining why your quiz answers were right or wrong
- Answering questions about how the AdaptiveTutor system works
- Motivating and supporting you throughout your learning journey

I remember the context of our current conversation so you can ask 
follow-up questions naturally. However, I do not remember previous 
separate conversations.

To get the best from me:
- Be specific in your questions ("Explain encapsulation in Java" works 
  better than "Explain OOP")
- Tell me what you already understand so I can build on it
- Ask me to give examples if an explanation is unclear

I am here to support your learning — not to do the work for you.
Always attempt questions yourself first before asking for help.
"""

# FUNCTIONS [unchanged signatures]

def get_hint(question_text: str, topic: str, difficulty: str) -> str:
    prompt = f"""A student is attempting this {difficulty} quiz question about {topic}:

Question: {question_text}

Give a helpful hint that guides them toward the answer WITHOUT revealing the answer.
Keep the hint to 2-3 sentences maximum."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=150,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def get_explanation(
    question_text: str,
    correct_answer: str,
    student_answer: str,
    is_correct: bool,
    topic: str
) -> str:
    status = "correctly" if is_correct else "incorrectly"
    prompt = f"""A student answered this Java question {status}.

Topic: {topic}
Question: {question_text}
Correct Answer: {correct_answer}
Student's Answer: {student_answer}

Provide a clear educational explanation of why the correct answer is right.
If the student was wrong, gently explain the misconception.
Keep the explanation to 3-4 sentences."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=200,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def grade_typed_answer(
    question_text: str,
    correct_answer: str,
    student_answer: str
) -> dict:
    prompt = f"""You are grading a typed answer from an undergraduate Java student.

Question: {question_text}
Expected Answer: {correct_answer}
Student's Answer: {student_answer}

Determine if the student's answer is correct based on meaning, not exact wording.
A student passes if their answer captures the core concept correctly.

Respond ONLY with valid JSON in exactly this format:
{{"is_correct": true or false, "reasoning": "one sentence explaining your decision"}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def chat_with_tutor(
    message: str,
    history: list,
    topic_context: str = None
) -> str:
    system = SYSTEM_PROMPT
    if topic_context:
        system += f"\n\nThe student is currently studying: {topic_context}. " \
                  f"Prioritize helping them with this topic if their question is related."

    messages = [{"role": "system", "content": system}]

    # Include last 10 messages for conversation context
    for msg in history[-10:]:
        messages.append({
            "role":    msg["role"],
            "content": msg["content"]
        })

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def generate_personalized_questions(
    topic_title: str,
    weak_subtopics: list,
    difficulty: str,
    curriculum_context: str,
    previous_question_ids: list,
    count: int = 10
) -> list:
    subtopic_list = "\n".join(f"- {s}" for s in weak_subtopics)
    difficulty_guidance = (
        "Focus on basic recall and definitions, but rephrase concepts differently "
        "from standard questions to help the student see it from a new angle."
        if difficulty == "easy"
        else
        "Focus on application and code analysis targeting the weak areas specifically."
    )

    prompt = f"""You are generating a personalized remedial quiz for a student who 
struggled with specific subtopics in a Java programming course.

TOPIC: {topic_title}
DIFFICULTY: {difficulty.upper()}
WEAK SUBTOPICS (student failed questions from these):
{subtopic_list}

CURRICULUM REFERENCE:
{curriculum_context}

DIFFICULTY GUIDANCE: {difficulty_guidance}

TASK:
Generate exactly {count} questions FOCUSED on the weak subtopics listed above.
- Mix: roughly 7 multiple choice and 3 typed
- For multiple choice: exactly 4 options labeled A, B, C, D
- Questions must approach the concepts from a fresh angle
- Each question should reinforce understanding of the specific weak area

Respond ONLY with a valid JSON array. No preamble, no markdown.
[
  {{
    "question_type": "multiple_choice",
    "question_text": "...",
    "subtopic": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_answer": "A. ...",
    "explanation": "..."
  }}
]"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3000,
        temperature=0.8,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

# Lesson content generation

def generate_lesson_content(
    topic_title: str,
    subtopics: list,
    curriculum_context: str,
    is_remedial: bool = False,
    weak_subtopics: list = None
) -> dict:
    """
    Generate deep, elaborated lesson content for a topic.
    If is_remedial=True, regenerate only weak subtopics in simpler language.
    """

    if is_remedial and weak_subtopics:
        subtopics_to_cover = weak_subtopics
        remedial_instruction = """This is a REMEDIAL lesson for a student who 
previously struggled with these subtopics. Your job is to explain these concepts 
DIFFERENTLY and MORE CLEARLY than a standard lesson would.

Requirements for remedial lessons:
- Start each subtopic by acknowledging what commonly confuses students about it
- Break every concept into the smallest possible steps
- Use simpler vocabulary — avoid heavy technical jargon
- Use at least 2 real-world analogies per subtopic to make abstract ideas concrete
- Show more code examples than usual, with detailed line-by-line explanations
- Explicitly point out the most common mistakes students make on this subtopic
- End each subtopic with 3 clear "Remember this" bullet points
- Be encouraging and patient in tone throughout"""
    else:
        subtopics_to_cover = subtopics
        remedial_instruction = """This is a first-time lesson for undergraduate students.
Your job is to teach these concepts thoroughly and engagingly.

Requirements:
- Explain every concept in depth — do not just define it, teach it
- Use real-world analogies to make abstract concepts relatable
- Provide multiple code examples per subtopic showing different use cases
- Include step-by-step breakdowns for any complex concept
- Point out common mistakes students make and how to avoid them
- End each subtopic with clear practice tips the student should remember
- Write as if you are a patient, knowledgeable lecturer speaking directly to the student
- Do not rush through any concept — depth and clarity are more important than brevity"""

    subtopic_list = "\n".join(f"- {s}" for s in subtopics_to_cover)

    prompt = f"""You are an expert Java programming lecturer generating a comprehensive 
lesson for undergraduate Computer Science students at Adeleke University.

TOPIC: {topic_title}

SUBTOPICS TO COVER:
{subtopic_list}

LECTURER'S CURRICULUM REFERENCE (your lesson MUST align with this content — 
use it as your guide for what concepts to cover and how deep to go):
{curriculum_context}

LESSON WRITING INSTRUCTIONS:
{remedial_instruction}

CRITICAL QUALITY REQUIREMENTS:
- Each subtopic section must be SUBSTANTIAL — minimum 150 words of explanation
- Do NOT just define terms — explain WHY they work the way they do
- Every code example must have a comment explaining what each line does
- Analogies must be relatable to everyday Nigerian student life where possible
- Common mistakes section must list at least 2 specific, realistic mistakes
- Practice tips must be actionable, not generic

TONE: Friendly, encouraging, academic. Write as if talking directly to the student.
Use "you" and "your" to make it personal. Avoid passive voice where possible.

Respond ONLY with valid JSON in exactly this structure. 
No preamble, no markdown fences, no extra text outside the JSON:

{{
  "topic_title": "{topic_title}",
  "is_remedial": {str(is_remedial).lower()},
  "introduction": "A warm, engaging 3-4 sentence introduction to the topic that tells the student what they will learn and why it matters in real Java development.",
  "subtopics": [
    {{
      "title": "exact subtopic name from the list above",
      "explanation": "Deep, thorough explanation of the concept. Minimum 150 words. Explain the what, the why, and the how. Write in a direct, engaging academic tone.",
      "analogy": "A relatable real-world analogy that makes this concept click. Should relate to everyday experiences a Nigerian university student would understand.",
      "code_examples": [
        {{
          "description": "what this code example demonstrates",
          "code": "the actual Java code with inline comments on each line",
          "output": "the expected output or result of running this code, if applicable"
        }},
        {{
          "description": "a second code example showing a different use case or variation",
          "code": "second Java code example with comments",
          "output": "expected output if applicable"
        }}
      ],
      "common_mistakes": [
        "First specific mistake students commonly make on this subtopic, explained clearly",
        "Second specific mistake students commonly make, with explanation of why it is wrong"
      ],
      "practice_tips": [
        "First actionable practice tip the student should remember and apply",
        "Second practice tip",
        "Third practice tip"
      ]
    }}
  ],
  "lesson_summary": "A solid 4-5 sentence summary that recaps the key points from every subtopic covered. This should serve as a quick reference the student can re-read before taking the quiz."
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        max_tokens=6000,
        temperature=0.6,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)