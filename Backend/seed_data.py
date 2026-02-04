"""
Seed script to populate the database with example data.

Run with: python seed_data.py
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domain import (
    Node, Edge, EdgeType, Graph,
    Question, QuestionMetadata, QuestionType, KnowledgeType,
    User, Community,
    QuestionBank
)


async def seed_database():
    """Populate the database with example data."""
    
    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("🌱 Seeding database with example data...\n")
    
    # 1. Create example knowledge graph
    print("📚 Creating knowledge graph nodes...")
    graph = Graph()
    
    nodes_data = [
        ("python_basics", "Python Basics", 0.7, 0.75, 1.0),
        ("variables", "Variables & Data Types", 0.65, 0.7, 0.9),
        ("functions", "Functions & Scope", 0.5, 0.55, 0.8),
        ("oop", "Object-Oriented Programming", 0.4, 0.45, 0.85),
        ("classes", "Classes & Objects", 0.35, 0.4, 0.8),
        ("inheritance", "Inheritance & Polymorphism", 0.2, 0.25, 0.75),
        ("decorators", "Decorators & Metaprogramming", 0.15, 0.2, 0.7),
        ("async", "Async & Concurrency", 0.1, 0.15, 0.65),
    ]
    
    for node_id, topic_name, proven, estimated, importance in nodes_data:
        node = Node(
            id=node_id,
            topic_name=topic_name,
            proven_knowledge_rating=proven,
            user_estimated_knowledge_rating=estimated,
            importance=importance,
            relevance=0.8,
            view_frequency=max(1, int(proven * 10))
        )
        graph.add_node(node)
        print(f"  ✓ {topic_name}")
    
    # 2. Create edges (prerequisites)
    print("\n🔗 Creating prerequisite relationships...")
    edges = [
        ("python_basics", "variables", EdgeType.PREREQUISITE, 1.0),
        ("variables", "functions", EdgeType.PREREQUISITE, 1.0),
        ("functions", "oop", EdgeType.PREREQUISITE, 1.0),
        ("oop", "classes", EdgeType.PREREQUISITE, 1.0),
        ("classes", "inheritance", EdgeType.PREREQUISITE, 1.0),
        ("classes", "decorators", EdgeType.APPLIED_WITH, 0.7),
        ("functions", "async", EdgeType.APPLIED_WITH, 0.8),
        ("python_basics", "functions", EdgeType.APPLIED_WITH, 0.6),
        ("oop", "inheritance", EdgeType.PREREQUISITE, 0.9),
        ("inheritance", "decorators", EdgeType.APPLIED_WITH, 0.7),
        ("variables", "oop", EdgeType.RELATED, 0.5),
        ("functions", "classes", EdgeType.RELATED, 0.8),
    ]
    
    for from_id, to_id, edge_type, weight in edges:
        edge = Edge(
            from_node_id=from_id,
            to_node_id=to_id,
            type=edge_type,
            weight=weight
        )
        graph.add_edge(edge)
        print(f"  ✓ {from_id} → {to_id} ({edge_type.value})")
    
    # 3. Create questions
    print("\n❓ Creating questions...")
    question_bank = QuestionBank()
    
    questions_data = [
        ("q1", "What is a variable in Python?", "A variable is a named container that stores a value", "variables", QuestionType.OPEN, 1),
        ("q2", "What are the basic data types in Python?", "int, float, str, bool, list, dict, tuple, set", "variables", QuestionType.MCQ, 2),
        ("q3", "What is the purpose of a function?", "Functions encapsulate reusable code blocks", "functions", QuestionType.OPEN, 2),
        ("q4", "How do you define a function in Python?", "Using the def keyword", "functions", QuestionType.MCQ, 1),
        ("q5", "What is a class in Python?", "A blueprint for creating objects", "classes", QuestionType.OPEN, 3),
        ("q6", "What is inheritance in OOP?", "A mechanism to inherit properties and methods from parent classes", "inheritance", QuestionType.OPEN, 3),
        ("q7", "What is polymorphism?", "The ability to have multiple forms or behaviors", "inheritance", QuestionType.MCQ, 4),
        ("q8", "What are decorators used for?", "Decorators modify the behavior of functions or classes", "decorators", QuestionType.OPEN, 4),
        ("q9", "What is async programming?", "Asynchronous programming allows concurrent execution", "async", QuestionType.OPEN, 5),
        ("q10", "What is OOP?", "Object-Oriented Programming is a paradigm based on objects and classes", "oop", QuestionType.OPEN, 2),
    ]
    
    now = datetime.now()
    for qid, text, answer, node_id, qtype, difficulty in questions_data:
        question = Question(
            id=qid,
            text=text,
            answer=answer,
            question_type=qtype,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=[node_id],
            metadata=QuestionMetadata(
                created_by="system",
                created_at=now - timedelta(days=difficulty),
                importance=difficulty * 0.2
            ),
            difficulty=difficulty,
            tags={"fundamentals", "python"},
            last_attempted_at=now - timedelta(days=1) if qid != "q1" else None
        )
        question_bank.add_question(question, graph)
        print(f"  ✓ {qid}: {text[:50]}...")
    
    # 4. Create communities
    print("\n👥 Creating communities...")
    communities = [
        ("python_fundamentals", "Python Fundamentals", "Learn the basics of Python programming", {"python_basics": 1.0, "variables": 1.0, "functions": 0.8}),
        ("advanced_python", "Advanced Python", "Master advanced concepts like OOP and decorators", {"oop": 1.5, "classes": 1.5, "decorators": 1.2, "inheritance": 1.0}),
        ("async_programming", "Async Programming", "Learn concurrent and asynchronous programming", {"async": 2.0, "functions": 1.0}),
    ]
    
    for comm_id, name, desc, importance_overrides in communities:
        community = Community(
            id=comm_id,
            name=name,
            description=desc,
            node_importance_overrides=importance_overrides
        )
        print(f"  ✓ {name}")
    
    # 5. Create users
    print("\n👤 Creating users...")
    users = [
        ("user1", "Alice Johnson", "alice@example.com", {"python_fundamentals"}),
        ("user2", "Bob Smith", "bob@example.com", {"advanced_python", "async_programming"}),
        ("user3", "Charlie Brown", "charlie@example.com", {"python_fundamentals", "advanced_python"}),
    ]
    
    for user_id, name, email, communities_joined in users:
        user = User(
            id=user_id,
            name=name,
            email=email,
            joined_community_ids=communities_joined
        )
        print(f"  ✓ {name} ({email})")
    
    print("\n" + "="*60)
    print("✅ Database seeding complete!")
    print("="*60)
    print(f"\nCreated:")
    print(f"  • {len(nodes_data)} knowledge nodes")
    print(f"  • {len(edges)} edges (relationships)")
    print(f"  • {len(questions_data)} questions")
    print(f"  • {len(communities)} communities")
    print(f"  • {len(users)} users")
    print(f"\nYour API is ready at: http://localhost:8000/api/v1")
    print(f"Frontend is ready at: http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(seed_database())
