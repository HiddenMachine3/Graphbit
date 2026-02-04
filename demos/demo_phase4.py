"""
Phase 4 Demo: Question Bank & Tagging System

Demonstrates:
1. Question enhancements (difficulty, tags, last_attempted_at)
2. QuestionBank CRUD operations
3. Coverage validation with graph integration
4. Query methods (by node, tag, difficulty, type)
5. Performance tracking
6. Realistic Python learning question bank
"""

from datetime import datetime, timedelta
from src.models import (
    QuestionBank,
    Question,
    QuestionMetadata,
    QuestionType,
    KnowledgeType,
    Graph,
    Node,
    Edge,
    EdgeType,
)


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_question(q: Question):
    """Print question details."""
    print(f"  [{q.id}] {q.text}")
    print(f"      Difficulty: {'⭐' * q.difficulty} ({q.difficulty}/5)")
    print(f"      Tags: {', '.join(q.tags) if q.tags else 'None'}")
    print(f"      Type: {q.question_type.value}")
    print(f"      Covers: {', '.join(q.covered_node_ids)}")
    if q.last_attempted_at:
        print(f"      Last Attempted: {q.last_attempted_at.strftime('%Y-%m-%d %H:%M')}")
    
    total_attempts = q.metadata.hits + q.metadata.misses
    if total_attempts > 0:
        print(f"      Success Rate: {q.success_rate:.1%} ({q.metadata.hits}/{total_attempts})")
    else:
        print(f"      Success Rate: N/A (0 attempts)")


def demo_question_enhancements():
    """Demonstrate enhanced Question model."""
    print_section("1. Question Model Enhancements")
    
    # Create question with new fields
    q = Question(
        id="q1",
        text="What is Python?",
        answer="A high-level, interpreted programming language",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=["python"],
        metadata=QuestionMetadata(
            created_by="instructor",
            created_at=datetime.now()
        ),
        difficulty=1,  # Easy question
        tags={"basics", "intro", "fundamentals"}
    )
    
    print("\n✅ Created question with difficulty and tags:")
    print_question(q)
    
    # Record attempts
    print("\n📝 Recording attempts...")
    now = datetime.now()
    q.record_attempt(success=True, timestamp=now)
    q.record_attempt(success=True, timestamp=now + timedelta(days=1))
    q.record_attempt(success=False, timestamp=now + timedelta(days=2))
    q.record_attempt(success=True, timestamp=now + timedelta(days=3))
    
    print("\n✅ After 4 attempts (3 correct, 1 incorrect):")
    print_question(q)


def demo_question_bank_basics():
    """Demonstrate QuestionBank CRUD operations."""
    print_section("2. QuestionBank CRUD Operations")
    
    bank = QuestionBank()
    
    # Create questions
    questions = [
        Question(
            id="q1",
            text="What is a variable?",
            answer="A named storage location",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["variables"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=1,
            tags={"basics", "variables"}
        ),
        Question(
            id="q2",
            text="What is a function?",
            answer="A reusable block of code",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["functions"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=2,
            tags={"intermediate", "functions"}
        ),
        Question(
            id="q3",
            text="Implement a function that adds two numbers",
            answer="def add(a, b): return a + b",
            question_type=QuestionType.OPEN,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["functions"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=3,
            tags={"intermediate", "coding"}
        ),
    ]
    
    # Add questions
    print("\n➕ Adding questions to bank...")
    for q in questions:
        bank.add_question(q)
        print(f"  Added: {q.id}")
    
    print(f"\n✅ Bank now contains {bank.count_questions()} questions")
    
    # Retrieve question
    print("\n🔍 Retrieving question q2:")
    q = bank.get_question("q2")
    print_question(q)
    
    # Remove question
    print("\n➖ Removing question q1...")
    bank.remove_question("q1")
    print(f"✅ Bank now contains {bank.count_questions()} questions")


def demo_coverage_validation():
    """Demonstrate graph-based coverage validation."""
    print_section("3. Coverage Validation with Graph")
    
    # Build knowledge graph
    graph = Graph()
    graph.add_node(Node(id="python", topic_name="Python Basics"))
    graph.add_node(Node(id="variables", topic_name="Variables"))
    graph.add_node(Node(id="functions", topic_name="Functions"))
    graph.add_node(Node(id="classes", topic_name="Classes"))
    graph.add_node(Node(id="java", topic_name="Java"))  # Disconnected node
    
    graph.add_edge(Edge(from_node_id="python", to_node_id="variables", type=EdgeType.PREREQUISITE, weight=1.0))
    graph.add_edge(Edge(from_node_id="variables", to_node_id="functions", type=EdgeType.PREREQUISITE, weight=1.0))
    graph.add_edge(Edge(from_node_id="functions", to_node_id="classes", type=EdgeType.PREREQUISITE, weight=1.0))
    
    print("\n📊 Knowledge Graph:")
    print("  python → variables → functions → classes")
    print("  java (disconnected)")
    
    bank = QuestionBank()
    
    # Valid single-node question
    print("\n✅ Adding question covering single node (python)...")
    q1 = Question(
        id="q1",
        text="What is Python?",
        answer="A programming language",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=["python"],
        metadata=QuestionMetadata(created_by="system", created_at=datetime.now())
    )
    bank.add_question(q1, graph=graph)
    print("  ✓ Success: Single node coverage is valid")
    
    # Valid multi-node question (connected nodes)
    print("\n✅ Adding question covering connected nodes (variables, functions)...")
    q2 = Question(
        id="q2",
        text="Explain variable scope in functions",
        answer="Variables can have local or global scope",
        question_type=QuestionType.OPEN,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=["variables", "functions"],
        metadata=QuestionMetadata(created_by="system", created_at=datetime.now())
    )
    bank.add_question(q2, graph=graph)
    print("  ✓ Success: Nodes are connected (variables → functions)")
    
    # Invalid: disconnected nodes
    print("\n❌ Attempting to add question with disconnected coverage (python, java)...")
    q3 = Question(
        id="q3",
        text="Compare Python and Java",
        answer="Both are OOP languages",
        question_type=QuestionType.OPEN,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=["python", "java"],
        metadata=QuestionMetadata(created_by="system", created_at=datetime.now())
    )
    try:
        bank.add_question(q3, graph=graph)
    except ValueError as e:
        print(f"  ✓ Validation failed as expected: {e}")
    
    # Invalid: nonexistent node
    print("\n❌ Attempting to add question with nonexistent node...")
    q4 = Question(
        id="q4",
        text="What is JavaScript?",
        answer="A web programming language",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.CONCEPT,
        covered_node_ids=["javascript"],
        metadata=QuestionMetadata(created_by="system", created_at=datetime.now())
    )
    try:
        bank.add_question(q4, graph=graph)
    except ValueError as e:
        print(f"  ✓ Validation failed as expected: {e}")
    
    print(f"\n✅ Bank contains {bank.count_questions()} valid questions")


def demo_query_methods():
    """Demonstrate various query methods."""
    print_section("4. Query Methods")
    
    bank = QuestionBank()
    
    # Create diverse question set
    questions = [
        # Python basics
        Question(
            id="q1",
            text="What is Python?",
            answer="A programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["python"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=1,
            tags={"basics", "intro"}
        ),
        # Variables
        Question(
            id="q2",
            text="How to declare a variable?",
            answer="name = value",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["variables"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=2,
            tags={"basics", "syntax"}
        ),
        # Functions
        Question(
            id="q3",
            text="Define a function",
            answer="def function_name():",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["functions"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=3,
            tags={"intermediate", "syntax"}
        ),
        # Advanced functions
        Question(
            id="q4",
            text="Explain decorators",
            answer="Functions that modify other functions",
            question_type=QuestionType.OPEN,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["functions"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=5,
            tags={"advanced", "decorators"}
        ),
        # MCQ
        Question(
            id="q5",
            text="Which is mutable? A) tuple B) list C) string D) int",
            answer="B",
            question_type=QuestionType.MCQ,
            knowledge_type=KnowledgeType.FACT,
            covered_node_ids=["python"],
            metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
            difficulty=3,
            tags={"intermediate", "data-structures"}
        ),
    ]
    
    for q in questions:
        bank.add_question(q)
    
    print(f"\n📚 Question Bank: {bank.count_questions()} questions")
    
    # Query by node
    print("\n🔍 Questions covering 'functions' node:")
    function_questions = bank.get_questions_by_node("functions")
    for q in function_questions:
        print(f"  - {q.id}: {q.text}")
    
    # Query by tag
    print("\n🏷️  Questions tagged 'basics':")
    basics_questions = bank.get_questions_by_tag("basics")
    for q in basics_questions:
        print(f"  - {q.id}: {q.text}")
    
    # Query by difficulty
    print("\n⭐ Easy questions (difficulty 1-2):")
    easy_questions = bank.get_questions_by_difficulty(1, 2)
    for q in easy_questions:
        print(f"  - {q.id}: {q.text} ({'⭐' * q.difficulty})")
    
    print("\n⭐⭐⭐⭐⭐ Hard questions (difficulty 4-5):")
    hard_questions = bank.get_questions_by_difficulty(4, 5)
    for q in hard_questions:
        print(f"  - {q.id}: {q.text} ({'⭐' * q.difficulty})")
    
    # Query by type
    print("\n📝 Flashcard questions:")
    flashcards = bank.get_questions_by_type(QuestionType.FLASHCARD)
    for q in flashcards:
        print(f"  - {q.id}: {q.text}")
    
    print("\n📝 Open-ended questions:")
    open_questions = bank.get_questions_by_type(QuestionType.OPEN)
    for q in open_questions:
        print(f"  - {q.id}: {q.text}")


def demo_performance_tracking():
    """Demonstrate performance tracking."""
    print_section("5. Performance Tracking")
    
    bank = QuestionBank()
    
    q = Question(
        id="q1",
        text="What is a list comprehension?",
        answer="[x for x in iterable]",
        question_type=QuestionType.FLASHCARD,
        knowledge_type=KnowledgeType.PROCEDURE,
        covered_node_ids=["python"],
        metadata=QuestionMetadata(created_by="system", created_at=datetime.now()),
        difficulty=3,
        tags={"intermediate", "syntax"}
    )
    
    bank.add_question(q)
    
    print("\n📝 Initial question state:")
    print_question(q)
    
    # Simulate study session
    print("\n📚 Simulating study session over 5 days...")
    now = datetime.now()
    
    results = [
        (1, True, "Day 1: Correct ✓"),
        (2, False, "Day 2: Incorrect ✗"),
        (3, True, "Day 3: Correct ✓"),
        (4, True, "Day 4: Correct ✓"),
        (5, True, "Day 5: Correct ✓"),
    ]
    
    for day, success, description in results:
        timestamp = now + timedelta(days=day-1)
        if success:
            bank.record_question_success("q1", timestamp)
        else:
            bank.record_question_failure("q1", timestamp)
        print(f"  {description}")
    
    # Show updated state
    updated_q = bank.get_question("q1")
    print("\n✅ Final question state:")
    print_question(updated_q)
    
    days_since_last = (datetime.now() - updated_q.last_attempted_at).days
    print(f"\n⏰ Days since last attempt: {days_since_last}")


def demo_realistic_python_bank():
    """Build a realistic Python learning question bank."""
    print_section("6. Realistic Python Learning Question Bank")
    
    # Build comprehensive knowledge graph
    graph = Graph()
    nodes = [
        Node(id="python-basics", topic_name="Python Fundamentals"),
        Node(id="variables", topic_name="Variables & Data Types"),
        Node(id="control-flow", topic_name="Control Flow"),
        Node(id="functions", topic_name="Functions"),
        Node(id="data-structures", topic_name="Data Structures"),
        Node(id="oop", topic_name="Object-Oriented Programming"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    edges = [
        Edge(from_node_id="python-basics", to_node_id="variables", type=EdgeType.PREREQUISITE, weight=1.0),
        Edge(from_node_id="variables", to_node_id="control-flow", type=EdgeType.PREREQUISITE, weight=1.0),
        Edge(from_node_id="control-flow", to_node_id="functions", type=EdgeType.PREREQUISITE, weight=1.0),
        Edge(from_node_id="functions", to_node_id="data-structures", type=EdgeType.PREREQUISITE, weight=1.0),
        Edge(from_node_id="data-structures", to_node_id="oop", type=EdgeType.PREREQUISITE, weight=1.0),
        Edge(from_node_id="variables", to_node_id="data-structures", type=EdgeType.DEPENDS_ON, weight=0.8),
        Edge(from_node_id="functions", to_node_id="oop", type=EdgeType.DEPENDS_ON, weight=0.9),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    print("\n📊 Learning Path:")
    print("  python-basics → variables → control-flow → functions → data-structures → oop")
    
    # Build question bank
    bank = QuestionBank()
    
    questions = [
        # Beginner questions
        Question(
            id="py-001",
            text="What is Python?",
            answer="A high-level, interpreted programming language",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["python-basics"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=1,
            tags={"beginner", "intro", "fundamentals"}
        ),
        Question(
            id="py-002",
            text="How do you create a variable in Python?",
            answer="variable_name = value",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["variables"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=1,
            tags={"beginner", "syntax", "variables"}
        ),
        Question(
            id="py-003",
            text="What are the basic data types in Python?",
            answer="int, float, str, bool",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.FACT,
            covered_node_ids=["variables"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=2,
            tags={"beginner", "data-types"}
        ),
        
        # Intermediate questions
        Question(
            id="py-004",
            text="Write a for loop that prints numbers 1 to 5",
            answer="for i in range(1, 6): print(i)",
            question_type=QuestionType.OPEN,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["control-flow"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=2,
            tags={"intermediate", "loops", "syntax"}
        ),
        Question(
            id="py-005",
            text="What is the difference between a list and a tuple?",
            answer="Lists are mutable, tuples are immutable",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["data-structures"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=3,
            tags={"intermediate", "data-structures", "mutability"}
        ),
        Question(
            id="py-006",
            text="Define a function that returns the sum of two numbers",
            answer="def add(a, b): return a + b",
            question_type=QuestionType.OPEN,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["functions"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=2,
            tags={"intermediate", "functions", "coding"}
        ),
        
        # Advanced questions
        Question(
            id="py-007",
            text="Explain the concept of a class in Python",
            answer="A blueprint for creating objects with attributes and methods",
            question_type=QuestionType.OPEN,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["oop"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=4,
            tags={"advanced", "oop", "classes"}
        ),
        Question(
            id="py-008",
            text="What is a list comprehension and why use it?",
            answer="A concise way to create lists: [x for x in iterable]",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["data-structures", "control-flow"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=4,
            tags={"advanced", "comprehensions", "syntax"}
        ),
        Question(
            id="py-009",
            text="Implement a class with __init__ and __str__ methods",
            answer="class MyClass:\\n    def __init__(self, value):\\n        self.value = value\\n    def __str__(self):\\n        return str(self.value)",
            question_type=QuestionType.OPEN,
            knowledge_type=KnowledgeType.PROCEDURE,
            covered_node_ids=["oop", "functions"],
            metadata=QuestionMetadata(created_by="instructor", created_at=datetime.now()),
            difficulty=5,
            tags={"advanced", "oop", "magic-methods"}
        ),
    ]
    
    print(f"\n➕ Adding {len(questions)} questions to bank...")
    for q in questions:
        bank.add_question(q, graph=graph)
    
    print(f"✅ Successfully added all questions\n")
    
    # Show statistics
    print("📊 Question Bank Statistics:")
    print(f"  Total Questions: {bank.count_questions()}")
    
    print("\n  By Difficulty:")
    for diff in range(1, 6):
        count = len(bank.get_questions_by_difficulty(diff, diff))
        print(f"    {'⭐' * diff}: {count} questions")
    
    print("\n  By Node Coverage:")
    for node in nodes:
        count = len(bank.get_questions_by_node(node.id))
        if count > 0:
            print(f"    {node.topic_name}: {count} questions")
    
    print("\n  Popular Tags:")
    all_tags = set()
    for q_id in bank.questions:
        all_tags.update(bank.get_question(q_id).tags)
    
    for tag in sorted(all_tags):
        count = len(bank.get_questions_by_tag(tag))
        print(f"    #{tag}: {count} questions")
    
    # Show sample questions by category
    print("\n📚 Sample Beginner Questions:")
    beginner = bank.get_questions_by_tag("beginner")
    for q in beginner[:2]:
        print(f"  • {q.text}")
    
    print("\n📚 Sample Advanced Questions:")
    advanced = bank.get_questions_by_tag("advanced")
    for q in advanced[:2]:
        print(f"  • {q.text}")


def main():
    """Run all Phase 4 demonstrations."""
    print("\n" + "="*70)
    print("  PHASE 4: QUESTION BANK & TAGGING SYSTEM")
    print("  Demonstration Suite")
    print("="*70)
    
    demo_question_enhancements()
    demo_question_bank_basics()
    demo_coverage_validation()
    demo_query_methods()
    demo_performance_tracking()
    demo_realistic_python_bank()
    
    print("\n" + "="*70)
    print("  ✅ All Phase 4 demonstrations completed successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
