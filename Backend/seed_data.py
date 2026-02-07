"""
Seed script to populate the database with example data.

Run with: python seed_data.py
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text, update
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domain import (
    Node, Edge, EdgeType, Graph,
    Question, QuestionMetadata, QuestionType, KnowledgeType,
    User, Community,
    QuestionBank
)
from app.models import Base, Question as QuestionModel


async def seed_database(reset_db: bool = False):
    """Populate the database with example data."""
    
    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    # Create all tables (optionally reset first)
    async with engine.begin() as conn:
        if reset_db:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        # Ensure MCQ options column exists for existing databases
        options_check = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='questions' AND column_name='options'"
            )
        )
        if options_check.scalar() is None:
            try:
                await conn.execute(text("ALTER TABLE questions ADD COLUMN options JSONB"))
            except Exception:
                await conn.execute(text("ALTER TABLE questions ADD COLUMN options JSON"))

        explanations_check = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='questions' AND column_name='option_explanations'"
            )
        )
        if explanations_check.scalar() is None:
            try:
                await conn.execute(text("ALTER TABLE questions ADD COLUMN option_explanations JSONB"))
            except Exception:
                await conn.execute(text("ALTER TABLE questions ADD COLUMN option_explanations JSON"))
    
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
        ("variables", "oop", EdgeType.DEPENDS_ON, 0.5),
        ("functions", "classes", EdgeType.DEPENDS_ON, 0.8),
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
    
    # 3. Create questions in database
    print("\n❓ Creating questions...")
    questions_data = [
        (
            "q1",
            "What is a variable in Python?",
            "A variable is a named container that stores a value",
            "variables",
            QuestionType.OPEN,
            1,
            None,
            None,
        ),
        (
            "q2",
            "What are the basic data types in Python?",
            "int, float, str, bool, list, dict, tuple, set",
            "variables",
            QuestionType.MCQ,
            2,
            [
                "int, float, str, bool, list, dict, tuple, set",
                "int, float, string, boolean, array, object",
                "integer, decimal, text, logical, collection, map",
                "number, decimal, character, logic, array, hash",
            ],
            {
                "int, float, str, bool, list, dict, tuple, set": "These are the standard core Python data types.",
                "int, float, string, boolean, array, object": "Python uses str, bool, list, and dict instead of these terms.",
                "integer, decimal, text, logical, collection, map": "These describe concepts but are not Python type names.",
                "number, decimal, character, logic, array, hash": "Python does not define these as built-in type names.",
            },
        ),
        (
            "q3",
            "What is the purpose of a function?",
            "Functions encapsulate reusable code blocks",
            "functions",
            QuestionType.OPEN,
            2,
            None,
            None,
        ),
        (
            "q4",
            "How do you define a function in Python?",
            "Using the def keyword",
            "functions",
            QuestionType.MCQ,
            1,
            [
                "Using the def keyword",
                "Using the function keyword",
                "Using the fn keyword",
                "Using the func keyword",
            ],
            {
                "Using the def keyword": "Python functions are defined with the def keyword.",
                "Using the function keyword": "Python does not use a function keyword.",
                "Using the fn keyword": "fn is not a Python keyword.",
                "Using the func keyword": "func is not a Python keyword.",
            },
        ),
            (
                "q5",
                "What is a class in Python?",
                "A blueprint for creating objects",
                "classes",
                QuestionType.OPEN,
                3,
                None,
                None,
            ),
            (
                "q6",
                "What is inheritance in OOP?",
                "A mechanism to inherit properties and methods from parent classes",
                "inheritance",
                QuestionType.OPEN,
                3,
                None,
                None,
            ),
            (
                "q7",
                "What is polymorphism?",
                "The ability to have multiple forms or behaviors",
                "inheritance",
                QuestionType.MCQ,
                4,
                [
                    "The ability to have multiple forms or behaviors",
                    "The process of inheritance",
                    "The ability to hide implementation details",
                    "The reuse of code through inheritance",
                ],
                {
                    "The ability to have multiple forms or behaviors": "Polymorphism means the same interface can have different implementations.",
                    "The process of inheritance": "Inheritance is related but is not polymorphism itself.",
                    "The ability to hide implementation details": "That describes encapsulation, not polymorphism.",
                    "The reuse of code through inheritance": "That's a benefit of inheritance, not polymorphism.",
                },
            ),
            (
                "q8",
                "What are decorators used for?",
                "Decorators modify the behavior of functions or classes",
                "decorators",
                QuestionType.OPEN,
                4,
                None,
                None,
            ),
            (
                "q9",
                "What is async programming?",
                "Asynchronous programming allows concurrent execution",
                "async",
                QuestionType.OPEN,
                5,
                None,
                None,
            ),
            (
                "q10",
                "What is OOP?",
                "Object-Oriented Programming is a paradigm based on objects and classes",
                "oop",
                QuestionType.OPEN,
                2,
                None,
                None,
            ),
        ]
    
    now = datetime.now()
    async with async_session() as session:
        existing_ids_result = await session.execute(select(QuestionModel.id))
        existing_ids = {row[0] for row in existing_ids_result.fetchall()}

        for (
            qid,
            question_text,
            answer,
            node_id,
            qtype,
            difficulty,
            options,
            option_explanations,
        ) in questions_data:
            if qid in existing_ids:
                if options:
                    await session.execute(
                        update(QuestionModel)
                        .where(QuestionModel.id == qid)
                        .values(options=options, option_explanations=option_explanations)
                    )
                    print(f"  ↻ {qid} exists, updated options")
                else:
                    print(f"  ↷ {qid} already exists, skipping")
                continue
            # Create domain Question for validation
            question_domain = Question(
                id=qid,
                text=question_text,
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
            
            # Create database Question model
            db_question = QuestionModel(
                id=qid,
                text=question_text,
                answer=answer,
                    options=options,
                option_explanations=option_explanations,
                question_type=qtype.value,
                knowledge_type=KnowledgeType.CONCEPT.value,
                covered_node_ids=[node_id],
                difficulty=difficulty,
                tags=list({"fundamentals", "python"}),
                question_metadata={
                    "created_by": "system",
                    "created_at": (now - timedelta(days=difficulty)).isoformat(),
                    "importance": difficulty * 0.2,
                    "hits": 0,
                    "misses": 0,
                },
                last_attempted_at=now - timedelta(days=1) if qid != "q1" else None,
                source_material_ids=[]
            )
            
            session.add(db_question)
            print(f"  ✓ {qid}: {question_text[:50]}...")
        
        await session.commit()
    
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
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    parser = argparse.ArgumentParser(description="Seed the database with example data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before seeding.",
    )
    args = parser.parse_args()

    asyncio.run(seed_database(reset_db=args.reset))
