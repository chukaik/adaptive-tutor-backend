import firebase_admin
from firebase_admin import credentials, firestore
import sys

SERVICE_ACCOUNT_PATH = "serviceAccountKey.json"

COURSE_STRUCTURE = {
    "course_title": "Data Structures",
    "course_code":  "CSC301",
    "faculty":      "Faculty of Science",
    "year_level":   3,
    "topics": [
        {
            "topic_index": 1,
            "title": "Introduction to Data Structures & Primitive Types",
            "prerequisite_topic_index": None,
            "ccmas_description": "Primitive types, Arrays, Records. Introduction to data structures and their importance in programming.",
            "subtopics": [
                {
                    "title": "What are Data Structures and Why They Matter",
                    "ccmas_notes": "Definition of data structures, importance in programming, classification into primitive and non-primitive, linear and non-linear. Real-world applications of data structures."
                },
                {
                    "title": "Primitive Types in C++",
                    "ccmas_notes": "int, float, double, char, bool, void in C++. Size, range and use cases of each. Type conversion and casting in C++."
                },
                {
                    "title": "Arrays in C++",
                    "ccmas_notes": "Array declaration and initialization in C++, accessing elements using index, array traversal, multi-dimensional arrays, passing arrays to functions, common array operations."
                },
                {
                    "title": "Records and Structs in C++",
                    "ccmas_notes": "struct keyword in C++, defining and using structs, accessing struct members with dot operator, arrays of structs, nested structs, difference between struct and class in C++."
                },
            ]
        },
        {
            "topic_index": 2,
            "title": "Strings & String Processing",
            "prerequisite_topic_index": 1,
            "ccmas_description": "Strings and String processing in C++.",
            "subtopics": [
                {
                    "title": "Introduction to Strings in C++",
                    "ccmas_notes": "C-style strings (char arrays) vs C++ string class. String declaration, initialization, null terminator in C-style strings. #include string header."
                },
                {
                    "title": "String Operations and Methods",
                    "ccmas_notes": "length(), size(), substr(), find(), replace(), append(), compare(), at(), c_str(). String concatenation with + operator. String input with getline()."
                },
                {
                    "title": "String Processing Techniques",
                    "ccmas_notes": "Iterating through strings character by character, converting between string and numeric types (stoi, stof, to_string), string tokenization, case conversion."
                },
                {
                    "title": "String Algorithms",
                    "ccmas_notes": "String reversal algorithm, palindrome check, counting occurrences of a character, finding substrings, string comparison algorithms. Implementation in C++."
                },
            ]
        },
        {
            "topic_index": 3,
            "title": "Memory, Stacks & Queues",
            "prerequisite_topic_index": 2,
            "ccmas_description": "Data representation in memory, Stack and Heap allocation, Queues. Implementation strategies for stacks and queues.",
            "subtopics": [
                {
                    "title": "Data Representation in Memory",
                    "ccmas_notes": "How data is stored in binary, memory addresses, bytes and bits. How variables are stored in memory. Memory layout of a C++ program."
                },
                {
                    "title": "Stack and Heap Allocation",
                    "ccmas_notes": "Stack memory — automatic allocation, LIFO, local variables, function call frames, stack overflow. Heap memory — dynamic allocation with new and delete, manual management, memory leaks."
                },
                {
                    "title": "Stack Data Structure",
                    "ccmas_notes": "Stack concept — LIFO principle. Operations: push, pop, peek/top, isEmpty, isFull. Array-based stack implementation in C++. Applications: function calls, undo operations, expression evaluation."
                },
                {
                    "title": "Queue Data Structure",
                    "ccmas_notes": "Queue concept — FIFO principle. Operations: enqueue, dequeue, front, rear, isEmpty, isFull. Array-based queue implementation in C++. Circular queue. Applications: scheduling, breadth-first search."
                },
                {
                    "title": "Implementation Strategies for Stacks and Queues",
                    "ccmas_notes": "Array-based vs linked list-based implementation. Trade-offs: fixed size vs dynamic size, memory overhead, time complexity of operations. C++ STL stack and queue."
                },
            ]
        },
        {
            "topic_index": 4,
            "title": "Trees",
            "prerequisite_topic_index": 3,
            "ccmas_description": "Trees. Implementation strategies for trees.",
            "subtopics": [
                {
                    "title": "Introduction to Trees",
                    "ccmas_notes": "Tree terminology: root, node, leaf, parent, child, sibling, height, depth, level. Types of trees: general tree, binary tree, binary search tree, balanced tree. Real-world applications."
                },
                {
                    "title": "Binary Trees and Binary Search Trees",
                    "ccmas_notes": "Binary tree definition — max 2 children per node. BST property — left child less than parent, right child greater. BST search, insertion and deletion. C++ struct-based node definition."
                },
                {
                    "title": "Tree Traversal",
                    "ccmas_notes": "In-order traversal (left, root, right), Pre-order traversal (root, left, right), Post-order traversal (left, right, root). Recursive implementation in C++. Output of each traversal on same tree."
                },
                {
                    "title": "Implementation Strategies for Trees",
                    "ccmas_notes": "Linked representation using nodes and pointers vs array representation. C++ implementation of binary tree using struct with left and right pointers. Memory considerations."
                },
            ]
        },
        {
            "topic_index": 5,
            "title": "Pointers, References & Linked Structures",
            "prerequisite_topic_index": 4,
            "ccmas_description": "Run time storage management, Pointers and References, linked structures.",
            "subtopics": [
                {
                    "title": "Pointers in C++",
                    "ccmas_notes": "Pointer declaration and initialization, address-of operator (&), dereference operator (*), pointer arithmetic, null pointer, pointer to pointer. Common pointer mistakes and how to avoid them."
                },
                {
                    "title": "References in C++",
                    "ccmas_notes": "Reference declaration, difference between pointer and reference, pass by reference vs pass by value, reference as function parameter, returning references from functions."
                },
                {
                    "title": "Run-time Storage Management",
                    "ccmas_notes": "Dynamic memory allocation with new and delete operators, dynamic arrays, memory leaks and how to prevent them, dangling pointers, smart pointers introduction."
                },
                {
                    "title": "Linked Lists",
                    "ccmas_notes": "Linked list concept — nodes connected by pointers. Types: singly linked, doubly linked, circular. Node structure in C++. Advantages over arrays: dynamic size, efficient insertion/deletion."
                },
                {
                    "title": "Linked List Operations",
                    "ccmas_notes": "Insertion at beginning, end, and middle. Deletion from beginning, end, and by value. Traversal and searching. Reversing a linked list. C++ implementation of each operation with full code."
                },
            ]
        },
        {
            "topic_index": 6,
            "title": "Algorithms — Searching & Sorting",
            "prerequisite_topic_index": 5,
            "ccmas_description": "Searching and sorting algorithms. Practical implementation using C++.",
            "subtopics": [
                {
                    "title": "Searching Algorithms",
                    "ccmas_notes": "Linear search — concept, C++ implementation, time complexity O(n). Binary search — concept, requirement for sorted array, C++ implementation iterative and recursive, time complexity O(log n). Comparison of both."
                },
                {
                    "title": "Bubble Sort",
                    "ccmas_notes": "Bubble sort concept — repeatedly swap adjacent elements. Step-by-step trace on example array. C++ implementation. Time complexity O(n²), space complexity O(1). When to use."
                },
                {
                    "title": "Selection Sort and Insertion Sort",
                    "ccmas_notes": "Selection sort — find minimum, place in position. Insertion sort — build sorted array one element at a time. C++ implementation of both. Time complexity analysis. Comparison with bubble sort."
                },
                {
                    "title": "Algorithm Analysis and Complexity",
                    "ccmas_notes": "Big O notation — what it means, why it matters. O(1), O(log n), O(n), O(n log n), O(n²). Best case, worst case, average case. Comparison of sorting algorithms by complexity. Choosing the right algorithm."
                },
            ]
        },
    ]
}


def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def upload_course(db, structure):
    print(f"\n🚀 Adding course: {structure['course_title']} ({structure['course_code']})")
    print("="*60)

    # Check if course already exists
    existing = db.collection("courses")\
                  .where("course_code", "==", structure["course_code"])\
                  .limit(1).stream()
    if any(True for _ in existing):
        print(f"⚠️  Course {structure['course_code']} already exists. Aborting.")
        print("   Run delete_course_data.py first if you want to re-add it.")
        sys.exit(0)

    # Create course document
    course_ref = db.collection("courses").document()
    course_id  = course_ref.id
    course_ref.set({
        "title":       structure["course_title"],
        "course_code": structure["course_code"],
        "description": f"Core undergraduate course — {structure['course_title']}",
        "faculty":     structure["faculty"],
        "year_level":  structure["year_level"],
        "created_at":  firestore.SERVER_TIMESTAMP,
    })
    print(f"\n📘 Course created — ID: {course_id}")

    topic_id_map = {}

    print(f"\n📚 Writing topics and curriculum guides...")

    for topic in structure["topics"]:
        topic_ref = db.collection("topics").document()
        topic_id  = topic_ref.id
        topic_id_map[topic["topic_index"]] = topic_id

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

        # Build curriculum guide from subtopics
        subtopics_for_firestore = []
        full_text_parts         = []

        for sub in topic["subtopics"]:
            content = f"CCMAS CURRICULUM NOTES: {sub['ccmas_notes']}"
            subtopics_for_firestore.append({
                "title":       sub["title"],
                "key_content": content,
            })
            full_text_parts.append(content)

        guide_ref = db.collection("curriculum_guides").document(topic_id)
        guide_ref.set({
            "topic_id":        topic_id,
            "course_id":       course_id,
            "topic_title":     topic["title"],
            "full_topic_text": " ".join(full_text_parts),
            "subtopics":       subtopics_for_firestore,
            "last_updated":    firestore.SERVER_TIMESTAMP,
        })

        print(f"\n   ✅ Topic {topic['topic_index']}: {topic['title']}")
        print(f"      ID          : {topic_id}")
        print(f"      Prerequisite: {prereq_id if prereq_id else 'None (first topic)'}")
        print(f"      Subtopics   : {len(topic['subtopics'])}")

    print("\n" + "="*60)
    print("✅ UPLOAD COMPLETE")
    print("="*60)
    print(f"\n  Course ID : {course_id}")
    print(f"  Topics    : {len(structure['topics'])} uploaded")
    print(f"\n📌 IMPORTANT — Save these IDs:")
    print(f"  Course ID → {course_id}")
    for index, tid in topic_id_map.items():
        label = structure["topics"][index - 1]["title"]
        print(f"  Topic {index} ID → {tid}  ({label})")

    print(f"\n📌 Next step: Run python seed/seed_csc301_questions.py")
    return course_id, topic_id_map


if __name__ == "__main__":
    db = init_firebase()
    upload_course(db, COURSE_STRUCTURE)
