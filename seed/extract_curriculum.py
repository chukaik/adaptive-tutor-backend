import fitz  # PyMuPDF
import json
import os

PDF_PATH = "seed/COS201.pdf"

# Pages that have relevant content from the PDF
# Topics not in the PDF will have empty page lists
# and will be AI-generated from CCMAS description
COURSE_STRUCTURE = {
    "course_title": "Computer Programming I",
    "course_code":  "COS201",
    "topics": [
        {
            "topic_index": 1,
            "title": "Introduction to Programming",
            "prerequisite_topic_index": None,
            "ccmas_description": "Essentials of computer programming. Types of programming: Functional programming, Declarative programming, Logic programming, object-oriented programming. Scripting languages, structured programming principles.",
            "subtopics": [
                {
                    "title": "Essentials of Computer Programming",
                    "pages": [],
                    "ccmas_notes": "What is programming, why we program, how computers execute instructions, the role of a programming language."
                },
                {
                    "title": "Types of Programming",
                    "pages": [],
                    "ccmas_notes": "Functional programming, Declarative programming, Logic programming, Object-Oriented programming — definitions, characteristics and examples of each."
                },
                {
                    "title": "Scripting Languages",
                    "pages": [],
                    "ccmas_notes": "What scripting languages are, how they differ from compiled languages, examples including JavaScript and Python."
                },
                {
                    "title": "Structured Programming Principles",
                    "pages": [],
                    "ccmas_notes": "Sequence, selection, iteration as the three core constructs. Top-down design, modular programming."
                },
            ]
        },
        {
            "topic_index": 2,
            "title": "Java Data Types, Variables & Operators",
            "prerequisite_topic_index": 1,
            "ccmas_description": "Basic data types, variables, expressions, assignment statements, and operators.",
            "subtopics": [
                {
                    "title": "Java Data Types Overview",
                    "pages": [2],
                    "ccmas_notes": "Two categories of data types in Java: primitive and non-primitive."
                },
                {
                    "title": "Primitive Data Types",
                    "pages": [3, 4, 5, 6, 7, 8, 9],
                    "ccmas_notes": "byte, short, int, long, float, double, char, boolean — ranges, sizes, use cases."
                },
                {
                    "title": "Non-Primitive Data Types",
                    "pages": [10, 11],
                    "ccmas_notes": "Arrays, Classes, Interfaces — how they differ from primitives."
                },
                {
                    "title": "Variables and Declarations",
                    "pages": [12, 13, 14, 15],
                    "ccmas_notes": "Variable declaration syntax, types of variables: local, instance, static/class, parameters."
                },
                {
                    "title": "Expressions, Assignment Statements and Operators",
                    "pages": [],
                    "ccmas_notes": "Arithmetic operators (+,-,*,/,%), relational operators, logical operators (&&, ||, !), assignment operators (=, +=, -=), increment/decrement (++, --), operator precedence."
                },
            ]
        },
        {
            "topic_index": 3,
            "title": "Control Structures & Arrays",
            "prerequisite_topic_index": 2,
            "ccmas_description": "Simple I/O; control structures; Arrays.",
            "subtopics": [
                {
                    "title": "Simple Input and Output",
                    "pages": [],
                    "ccmas_notes": "Scanner class for input, System.out.println for output, reading different data types from user."
                },
                {
                    "title": "Control Structures",
                    "pages": [],
                    "ccmas_notes": "if statement, if-else, nested if-else, switch statement — syntax and examples in Java."
                },
                {
                    "title": "Loops",
                    "pages": [],
                    "ccmas_notes": "for loop, while loop, do-while loop — syntax, use cases, differences, break and continue statements."
                },
                {
                    "title": "Arrays",
                    "pages": [],
                    "ccmas_notes": "Array declaration, initialization, accessing elements, array length, iterating arrays, multi-dimensional arrays, common array operations."
                },
            ]
        },
        {
            "topic_index": 4,
            "title": "Object-Oriented Programming Concepts",
            "prerequisite_topic_index": 3,
            "ccmas_description": "Basic object-oriented concepts: abstraction, objects, classes, methods; parameter passing; encapsulation.",
            "subtopics": [
                {
                    "title": "Introduction to Objects and Classes",
                    "pages": [17, 18, 19],
                    "ccmas_notes": "What objects and classes are, state and behaviour, creating objects with new keyword."
                },
                {
                    "title": "The Four Pillars of OOP",
                    "pages": [19, 20, 21],
                    "ccmas_notes": "Encapsulation, Inheritance, Polymorphism, Abstraction — definitions and examples."
                },
                {
                    "title": "Methods and Parameter Passing",
                    "pages": [],
                    "ccmas_notes": "Defining methods, return types, parameters, pass by value in Java, method overloading."
                },
                {
                    "title": "Access Modifiers and Encapsulation",
                    "pages": [22, 23, 24],
                    "ccmas_notes": "public, private, protected, default — scope and usage. Getters and setters."
                },
                {
                    "title": "Java Applications",
                    "pages": [25],
                    "ccmas_notes": "Java Applications, Java Applets, Java Servlets — types and differences."
                },
            ]
        },
        {
            "topic_index": 5,
            "title": "Class Hierarchies & Packages",
            "prerequisite_topic_index": 4,
            "ccmas_description": "Class hierarchies and programme organization using packages/namespaces.",
            "subtopics": [
                {
                    "title": "Inheritance",
                    "pages": [20],
                    "ccmas_notes": "extends keyword, parent and child classes, inheriting methods and fields, method overriding, super keyword."
                },
                {
                    "title": "Polymorphism",
                    "pages": [20],
                    "ccmas_notes": "Method overloading vs overriding, runtime polymorphism, compile-time polymorphism."
                },
                {
                    "title": "Package Fundamentals",
                    "pages": [26, 27, 28],
                    "ccmas_notes": "What packages are, why we use them, naming conventions, package declaration."
                },
                {
                    "title": "Types of Packages",
                    "pages": [28, 29, 30],
                    "ccmas_notes": "Pre-defined packages (java.lang, java.io, java.util etc.) and user-defined packages."
                },
                {
                    "title": "Accessing Packages",
                    "pages": [31, 32, 33, 34],
                    "ccmas_notes": "import keyword, importing specific classes, importing entire packages, fully qualified names."
                },
            ]
        },
        {
            "topic_index": 6,
            "title": "Strings & String Processing",
            "prerequisite_topic_index": 5,
            "ccmas_description": "Introduction to Strings and string processing.",
            "subtopics": [
                {
                    "title": "Introduction to Strings",
                    "pages": [],
                    "ccmas_notes": "String class in Java, String immutability, creating strings, string literals vs new String()."
                },
                {
                    "title": "String Methods and Operations",
                    "pages": [],
                    "ccmas_notes": "length(), charAt(), substring(), indexOf(), toUpperCase(), toLowerCase(), trim(), replace(), equals(), compareTo(), contains()."
                },
                {
                    "title": "String Processing Techniques",
                    "pages": [],
                    "ccmas_notes": "String concatenation, StringBuilder for mutable strings, converting between strings and other types, splitting strings."
                },
                {
                    "title": "Common String Algorithms",
                    "pages": [],
                    "ccmas_notes": "String reversal, palindrome check, counting characters, finding substrings, string comparison algorithms."
                },
            ]
        },
        {
            "topic_index": 7,
            "title": "APIs, Collections, Searching & Sorting",
            "prerequisite_topic_index": 6,
            "ccmas_description": "Use of API - use of iterators/enumerators, List, Stack, Queue from API. Searching; sorting.",
            "subtopics": [
                {
                    "title": "Use of API and Iterators",
                    "pages": [],
                    "ccmas_notes": "What an API is, Java standard library as an API, Iterator interface, using iterators to traverse collections, for-each loop."
                },
                {
                    "title": "List, Stack and Queue",
                    "pages": [],
                    "ccmas_notes": "ArrayList, LinkedList as List implementations. Stack class — push, pop, peek. Queue interface — offer, poll, peek. Use cases for each."
                },
                {
                    "title": "Searching Algorithms",
                    "pages": [],
                    "ccmas_notes": "Linear search — logic, implementation, time complexity. Binary search — logic, requirement for sorted array, implementation, time complexity."
                },
                {
                    "title": "Sorting Algorithms",
                    "pages": [],
                    "ccmas_notes": "Bubble sort, Selection sort, Insertion sort — step-by-step logic, Java implementation, time complexity comparison."
                },
            ]
        },
        {
            "topic_index": 8,
            "title": "Recursion & Exception Handling",
            "prerequisite_topic_index": 7,
            "ccmas_description": "Simple recursive algorithms, inheritance, polymorphism. Event-driven programming: event-handling methods; event propagation; exception handling.",
            "subtopics": [
                {
                    "title": "Introduction to Recursion",
                    "pages": [],
                    "ccmas_notes": "What recursion is, base case, recursive case, how the call stack works, when to use recursion."
                },
                {
                    "title": "Simple Recursive Algorithms",
                    "pages": [],
                    "ccmas_notes": "Factorial, Fibonacci, sum of array, binary search recursively — step-by-step trace of each."
                },
                {
                    "title": "Introduction to Exceptions",
                    "pages": [36, 37],
                    "ccmas_notes": "What exceptions are, normal flow disruption, why exception handling is necessary."
                },
                {
                    "title": "Exception Hierarchy and Types",
                    "pages": [38, 39, 40, 41, 42, 43, 44, 45, 46],
                    "ccmas_notes": "Throwable, Exception, Error. Checked vs unchecked exceptions. Common examples."
                },
                {
                    "title": "Exception Handling Mechanisms",
                    "pages": [47, 48, 49, 51, 52, 53, 54, 55, 56, 57, 59, 60, 61],
                    "ccmas_notes": "try, catch, finally, throw, throws — syntax and usage for each."
                },
            ]
        },
    ]
}


def extract_page_text(doc, page_number):
    page  = doc[page_number - 1]
    text  = page.get_text("text").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines)


def extract_curriculum(pdf_path, structure):
    print(f"\n📄 Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"   Total pages: {len(doc)}")

    result = {
        "course_title": structure["course_title"],
        "course_code":  structure["course_code"],
        "topics":       []
    }

    for topic in structure["topics"]:
        print(f"\n📚 Topic {topic['topic_index']}: {topic['title']}")
        topic_full_text    = []
        extracted_subtopics = []

        for subtopic in topic["subtopics"]:
            print(f"   → {subtopic['title']} (pages: {subtopic['pages'] or 'none — CCMAS only'})")
            subtopic_parts = []

            # Extract from PDF pages if available
            for page_num in subtopic["pages"]:
                try:
                    text = extract_page_text(doc, page_num)
                    if text:
                        subtopic_parts.append(text)
                except Exception as e:
                    print(f"     ⚠️  Page {page_num} error: {e}")

            pdf_text = " ".join(subtopic_parts)

            # Build combined content: PDF text + CCMAS notes
            combined_parts = []
            if pdf_text:
                combined_parts.append(f"LECTURE NOTES: {pdf_text}")
            combined_parts.append(f"CCMAS CURRICULUM NOTES: {subtopic['ccmas_notes']}")
            combined = " | ".join(combined_parts)

            extracted_subtopics.append({
                "title":          subtopic["title"],
                "pages":          subtopic["pages"],
                "extracted_text": combined,
                "has_pdf_content": len(pdf_text) > 0,
                "word_count":     len(combined.split()),
            })
            topic_full_text.append(combined)

        result["topics"].append({
            "topic_index":             topic["topic_index"],
            "title":                   topic["title"],
            "prerequisite_topic_index": topic["prerequisite_topic_index"],
            "ccmas_description":       topic["ccmas_description"],
            "subtopics":               extracted_subtopics,
            "full_topic_text":         " ".join(topic_full_text),
            "total_word_count":        len(" ".join(topic_full_text).split()),
        })

    doc.close()
    return result


def preview_extraction(data):
    print("\n" + "="*60)
    print("📋 EXTRACTION SUMMARY")
    print("="*60)
    print(f"Course: {data['course_title']} ({data['course_code']})")
    print(f"Topics: {len(data['topics'])}\n")

    for topic in data["topics"]:
        print(f"Topic {topic['topic_index']}: {topic['title']}")
        print(f"  Total words: {topic['total_word_count']}")
        for sub in topic["subtopics"]:
            source = "📄 PDF+CCMAS" if sub["has_pdf_content"] else "📝 CCMAS only"
            print(f"  {source} | {sub['title']} — {sub['word_count']} words")
        print()


def save_extraction(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved to: {output_path}")


if __name__ == "__main__":
    output_file = "seed/curriculum_extracted.json"
    extracted   = extract_curriculum(PDF_PATH, COURSE_STRUCTURE)
    preview_extraction(extracted)
    save_extraction(extracted, output_file)
    print("\n📌 Next step: Review seed/curriculum_extracted.json")
    print("   Then run: python seed/upload_curriculum.py")
