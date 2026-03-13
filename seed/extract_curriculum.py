import fitz  # PyMuPDF
import json
import os

# CONFIGURATION

PDF_PATH = "seed/COS201.pdf"

# Define exactly which pages belong to each topic and subtopic
COURSE_STRUCTURE = {
    "course_title": "Computer Programming I",
    "course_code": "COS201",
    "topics": [
        {
            "topic_index": 1,
            "title": "Java Data Types & Variables",
            "prerequisite_topic_index": None,  # First topic, no prerequisite
            "subtopics": [
                {"title": "Java Data Types Overview",        "pages": [2]},
                {"title": "Primitive Data Types",            "pages": [3, 4, 5, 6, 7, 8, 9]},
                {"title": "Non-Primitive Data Types",        "pages": [10, 11]},
                {"title": "Variables Overview",              "pages": [12]},
                {"title": "Types of Variables",              "pages": [13, 14, 15]},
            ]
        },
        {
            "topic_index": 2,
            "title": "Object-Oriented Programming (OOP) Concepts",
            "prerequisite_topic_index": 1,
            "subtopics": [
                {"title": "Introduction to Objects",                          "pages": [17]},
                {"title": "Classes",                                          "pages": [18, 19]},
                {"title": "The Four Pillars of OOP",                         "pages": [19, 20, 21]},
                {"title": "Access Modifiers",                                 "pages": [22, 23, 24]},
                {"title": "Java Applications (Applets, Applications, Servlets)", "pages": [25]},
            ]
        },
        {
            "topic_index": 3,
            "title": "Java Packages",
            "prerequisite_topic_index": 2,
            "subtopics": [
                {"title": "Package Fundamentals",  "pages": [26, 27, 28]},
                {"title": "Types of Packages",     "pages": [28, 29, 30]},
                {"title": "Accessing Packages",    "pages": [31, 32, 33, 34]},
            ]
        },
        {
            "topic_index": 4,
            "title": "Exception Handling",
            "prerequisite_topic_index": 3,
            "subtopics": [
                {"title": "Introduction to Exceptions", "pages": [36, 37]},
                {"title": "Types of Exceptions",        "pages": [38, 39, 40, 41, 42]},
                {"title": "Exception Hierarchy",        "pages": [43, 44, 45, 46]},
                {"title": "Handling Mechanisms",        "pages": [47, 48, 49, 51, 52,
                                                                   53, 54, 55, 56, 57,
                                                                   59, 60, 61]},
            ]
        },
    ]
}

# EXTRACTION LOGIC

def extract_page_text(doc, page_number):
    """Extract clean text from a single PDF page (1-indexed)."""
    page = doc[page_number - 1]  # PyMuPDF is 0-indexed
    text = page.get_text("text").strip()
    # Clean up excessive whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines)


def extract_curriculum(pdf_path: str, structure: dict) -> dict:
    """Extract text from PDF and organize it by topic and subtopic."""
    print(f"\n📄 Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"   Total pages found: {len(doc)}")

    result = {
        "course_title": structure["course_title"],
        "course_code": structure["course_code"],
        "topics": []
    }

    for topic in structure["topics"]:
        print(f"\n📚 Extracting Topic {topic['topic_index']}: {topic['title']}")
        topic_full_text = []
        extracted_subtopics = []

        for subtopic in topic["subtopics"]:
            print(f"   → Subtopic: {subtopic['title']} (pages {subtopic['pages']})")
            subtopic_text_parts = []

            for page_num in subtopic["pages"]:
                try:
                    text = extract_page_text(doc, page_num)
                    if text:
                        subtopic_text_parts.append(text)
                except Exception as e:
                    print(f"     ⚠️  Could not extract page {page_num}: {e}")

            combined = " ".join(subtopic_text_parts)
            extracted_subtopics.append({
                "title": subtopic["title"],
                "pages": subtopic["pages"],
                "extracted_text": combined,
                "word_count": len(combined.split())
            })
            topic_full_text.append(combined)

        result["topics"].append({
            "topic_index": topic["topic_index"],
            "title": topic["title"],
            "prerequisite_topic_index": topic["prerequisite_topic_index"],
            "subtopics": extracted_subtopics,
            "full_topic_text": " ".join(topic_full_text),
            "total_word_count": len(" ".join(topic_full_text).split())
        })

    doc.close()
    return result


def save_extraction(data: dict, output_path: str):
    """Save extracted curriculum to a JSON file for review."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Extraction complete. Saved to: {output_path}")


def preview_extraction(data: dict):
    """Print a summary of what was extracted for quick review."""
    print("\n" + "="*60)
    print("📋 EXTRACTION SUMMARY — Review before uploading to Firestore")
    print("="*60)
    print(f"Course: {data['course_title']} ({data['course_code']})")
    print(f"Topics extracted: {len(data['topics'])}\n")

    for topic in data["topics"]:
        print(f"Topic {topic['topic_index']}: {topic['title']}")
        print(f"  Total words: {topic['total_word_count']}")
        for sub in topic["subtopics"]:
            status = "✅" if sub["word_count"] > 20 else "⚠️  LOW CONTENT"
            print(f"  {status} {sub['title']} — {sub['word_count']} words")
        print()


# MAIN

if __name__ == "__main__":
    output_file = "seed/curriculum_extracted.json"

    # Run extraction
    extracted = extract_curriculum(PDF_PATH, COURSE_STRUCTURE)

    # Show summary in terminal
    preview_extraction(extracted)

    # Save to JSON for your review
    save_extraction(extracted, output_file)

    print("\n📌 Next step: Review seed/curriculum_extracted.json")
    print("   Then run: python seed/upload_curriculum.py")