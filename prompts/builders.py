"""
Prompt builders.

Each function takes plain arguments and returns the list of chat messages
sent to the model. None of them call the API; services/openai_service.py
does that.
"""
from prompts.system import SYSTEM_PROMPT


def course_label(course: dict | None) -> str:
    """
    The course as named in prompts: the course document's title, followed by
    its programming language in brackets when the document has a "language"
    field, e.g. "Data Structures (C++)". Falls back to "Computer Science".
    """
    if not course or not course.get("title"):
        return "Computer Science"
    language = course.get("language")
    return f"{course['title']} ({language})" if language else course["title"]


def build_curriculum_context(guide: dict | None) -> str:
    """
    Turn a curriculum_guides document into the reference text that grounds
    lesson and quiz prompts. Returns "" when there is no guide.
    """
    if not guide:
        return ""
    lines = [f"Topic: {guide.get('topic_title', '')}"]
    for sub in guide.get("subtopics", []):
        lines.append(f"\nSubtopic: {sub['title']}")
        lines.append(sub.get("key_content", ""))
    return "\n".join(lines)


def hint_messages(question_text: str, topic: str, difficulty: str) -> list[dict]:
    prompt = f"""A student is attempting this {difficulty} quiz question about {topic}:

Question: {question_text}

Give a helpful hint that guides them toward the answer WITHOUT revealing the answer.
Keep the hint to 2-3 sentences maximum."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt}
    ]


def explanation_messages(
    question_text: str,
    correct_answer: str,
    student_answer: str,
    is_correct: bool,
    topic: str,
    *,
    course: str
) -> list[dict]:
    status = "correctly" if is_correct else "incorrectly"
    prompt = f"""A student answered this {course} question {status}.

Topic: {topic}
Question: {question_text}
Correct Answer: {correct_answer}
Student's Answer: {student_answer}

Provide a clear educational explanation of why the correct answer is right.
If the student was wrong, gently explain the misconception.
Keep the explanation to 3-4 sentences."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt}
    ]


def grading_messages(
    question_text: str,
    correct_answer: str,
    student_answer: str,
    *,
    course: str
) -> list[dict]:
    prompt = f"""You are grading a typed answer from an undergraduate {course} student.

Question: {question_text}
Expected Answer: {correct_answer}
Student's Answer: {student_answer}

Determine if the student's answer is correct based on meaning, not exact wording.
A student passes if their answer captures the core concept correctly.

Respond ONLY with valid JSON in exactly this format:
{{"is_correct": true or false, "reasoning": "one sentence explaining your decision"}}"""

    return [{"role": "user", "content": prompt}]


def chat_messages(
    message: str,
    history: list,
    topic_context: str = None
) -> list[dict]:
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
    return messages


def personalized_quiz_messages(
    topic_title: str,
    weak_subtopics: list,
    difficulty: str,
    curriculum_context: str,
    count: int = 10,
    *,
    course: str
) -> list[dict]:
    subtopic_list = "\n".join(f"- {s}" for s in weak_subtopics)
    difficulty_guidance = (
        "Focus on basic recall and definitions, but rephrase concepts differently "
        "from standard questions to help the student see it from a new angle."
        if difficulty == "easy"
        else
        "Focus on application and code analysis targeting the weak areas specifically."
    )

    prompt = f"""You are generating a personalized remedial quiz for a student who 
struggled with specific subtopics in a {course} programming course.

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

    return [{"role": "user", "content": prompt}]


def lesson_messages(
    topic_title: str,
    subtopics: list,
    curriculum_context: str,
    is_remedial: bool = False,
    weak_subtopics: list = None,
    *,
    course: str
) -> list[dict]:
    """
    Messages for a full lesson, or, when is_remedial is True and
    weak_subtopics is non-empty, a simpler lesson on those subtopics only.
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

    prompt = f"""You are an expert {course} programming lecturer generating a comprehensive 
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
  "introduction": "A warm, engaging 3-4 sentence introduction to the topic that tells the student what they will learn and why it matters in real {course} development.",
  "subtopics": [
    {{
      "title": "exact subtopic name from the list above",
      "explanation": "Deep, thorough explanation of the concept. Minimum 150 words. Explain the what, the why, and the how. Write in a direct, engaging academic tone.",
      "analogy": "A relatable real-world analogy that makes this concept click. Should relate to everyday experiences a Nigerian university student would understand.",
      "code_examples": [
        {{
          "description": "what this code example demonstrates",
          "code": "the actual {course} code with inline comments on each line",
          "output": "the expected output or result of running this code, if applicable"
        }},
        {{
          "description": "a second code example showing a different use case or variation",
          "code": "second {course} code example with comments",
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

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt}
    ]
