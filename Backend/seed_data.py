"""
Seed script to populate the database with example data.

Creates projects as primary owners of knowledge graphs,
with communities applying overrides on top.

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
    User, Community, Project, ProjectVisibility,
    QuestionBank, UserNodeState
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
    
    now = datetime.now()
    
    # 1. Create user
    print("👤 Creating user...")
    user = User(
        id="user1",
        name="Alice Johnson",
        email="alice@example.com",
        joined_community_ids=set()
    )
    print(f"  ✓ {user.name} ({user.email})")
    
    # 2. Create projects
    print("\n📁 Creating projects...")
    projects = [
        Project(
            id="python_project",
            name="Python Programming",
            description="Learn Python from basics to advanced concepts",
            owner_id=user.id,
            visibility=ProjectVisibility.PUBLIC,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=1),
        ),
        Project(
            id="dsa_project",
            name="Data Structures & Algorithms",
            description="Master DSA concepts and problem solving",
            owner_id=user.id,
            visibility=ProjectVisibility.PUBLIC,
            created_at=now - timedelta(days=25),
            updated_at=now - timedelta(days=2),
        ),
        Project(
            id="biology_project",
            name="Biology Fundamentals",
            description="Explore biology concepts from cells to ecosystems",
            owner_id=user.id,
            visibility=ProjectVisibility.SHARED,
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=3),
        ),
    ]
    
    for project in projects:
        print(f"  ✓ {project.name}")
    
    # 3. Create community and attach all projects
    print("\n👥 Creating community...")
    community = Community(
        id="learning_hub",
        name="Learning Hub",
        description="A community for collaborative learning across all projects",
        project_ids={p.id for p in projects},
        node_importance_overrides={},
        question_importance_overrides={}
    )
    user.join_community(community.id)
    print(f"  ✓ {community.name}")
    print(f"  ✓ Attached {len(projects)} projects to community")
    
    # 4. Seed data for each project
    project_data = {
        "python_project": {
            "nodes": [
                ("py_basics", "Python Basics", 0.7, 0.75, 1.0),
                ("py_variables", "Variables & Data Types", 0.65, 0.7, 0.9),
                ("py_functions", "Functions & Scope", 0.5, 0.55, 0.8),
                ("py_oop", "Object-Oriented Programming", 0.4, 0.45, 0.85),
                ("py_classes", "Classes & Objects", 0.35, 0.4, 0.8),
            ],
            "edges": [
                ("py_basics", "py_variables", EdgeType.PREREQUISITE, 1.0),
                ("py_variables", "py_functions", EdgeType.PREREQUISITE, 1.0),
                ("py_functions", "py_oop", EdgeType.PREREQUISITE, 1.0),
                ("py_oop", "py_classes", EdgeType.PREREQUISITE, 1.0),
            ],
            "questions": [
                ("py_q1", "What is a variable in Python?", "A variable is a named container that stores a value", "py_variables", 1),
                ("py_q2", "How do you define a function in Python?", "Using the def keyword", "py_functions", 2),
                ("py_q3", "What is a class in Python?", "A blueprint for creating objects", "py_classes", 3),
            ],
            "community_overrides": {
                "py_basics": 1.2,
                "py_variables": 1.1,
            }
        },
        "dsa_project": {
            "nodes": [
                ("dsa_arrays", "Arrays & Lists", 0.6, 0.65, 0.9),
                ("dsa_stacks", "Stacks & Queues", 0.4, 0.45, 0.85),
                ("dsa_trees", "Trees & Graphs", 0.3, 0.35, 0.95),
                ("dsa_sorting", "Sorting Algorithms", 0.5, 0.55, 0.8),
            ],
            "edges": [
                ("dsa_arrays", "dsa_stacks", EdgeType.PREREQUISITE, 1.0),
                ("dsa_arrays", "dsa_sorting", EdgeType.PREREQUISITE, 0.8),
                ("dsa_stacks", "dsa_trees", EdgeType.PREREQUISITE, 0.9),
            ],
            "questions": [
                ("dsa_q1", "What is an array?", "A contiguous data structure for storing elements", "dsa_arrays", 1),
                ("dsa_q2", "What is a stack?", "A LIFO (Last In First Out) data structure", "dsa_stacks", 2),
                ("dsa_q3", "What is a binary tree?", "A tree where each node has at most two children", "dsa_trees", 3),
            ],
            "community_overrides": {
                "dsa_trees": 1.5,
                "dsa_sorting": 1.3,
            }
        },
        "biology_project": {
            "nodes": [
                ("bio_cells", "Cell Structure", 0.5, 0.55, 0.9),
                ("bio_dna", "DNA & Genetics", 0.4, 0.45, 0.95),
                ("bio_evolution", "Evolution", 0.3, 0.35, 0.85),
                ("bio_ecology", "Ecology & Ecosystems", 0.35, 0.4, 0.8),
            ],
            "edges": [
                ("bio_cells", "bio_dna", EdgeType.PREREQUISITE, 1.0),
                ("bio_dna", "bio_evolution", EdgeType.PREREQUISITE, 0.9),
                ("bio_cells", "bio_ecology", EdgeType.APPLIED_WITH, 0.7),
            ],
            "questions": [
                ("bio_q1", "What is the basic unit of life?", "The cell", "bio_cells", 1),
                ("bio_q2", "What does DNA stand for?", "Deoxyribonucleic Acid", "bio_dna", 2),
                ("bio_q3", "What is natural selection?", "The process where organisms better adapted to their environment survive", "bio_evolution", 3),
            ],
            "community_overrides": {
                "bio_dna": 1.4,
            }
        },
    }
    
    print("\n📚 Seeding project data...")
    async with async_session() as session:
        for project in projects:
            print(f"\n  Project: {project.name}")
            data = project_data[project.id]
            
            # Create graph for project
            graph = Graph(project_id=project.id)
            
            # Create nodes
            print(f"    Creating {len(data['nodes'])} nodes...")
            for node_id, topic_name, proven, estimated, importance in data["nodes"]:
                node = Node(
                    id=node_id,
                    project_id=project.id,
                    topic_name=topic_name,
                    proven_knowledge_rating=proven,
                    user_estimated_knowledge_rating=estimated,
                    importance=importance,
                    relevance=0.8,
                    view_frequency=max(1, int(proven * 10))
                )
                graph.add_node(node)
                
                # Create user node state for this user
                user_state = UserNodeState(
                    user_id=user.id,
                    project_id=project.id,
                    node_id=node_id,
                    proven_knowledge_rating=proven,
                    review_count=int(proven * 10),
                    last_reviewed_at=now - timedelta(days=int((1 - proven) * 10)),
                    stability=1.0 + proven
                )
                print(f"      ✓ {topic_name}")
            
            # Create edges
            print(f"    Creating {len(data['edges'])} edges...")
            for from_id, to_id, edge_type, weight in data["edges"]:
                edge = Edge(
                    project_id=project.id,
                    from_node_id=from_id,
                    to_node_id=to_id,
                    type=edge_type,
                    weight=weight
                )
                graph.add_edge(edge)
                print(f"      ✓ {from_id} → {to_id}")
            
            # Create questions
            print(f"    Creating {len(data['questions'])} questions...")
            existing_ids_result = await session.execute(select(QuestionModel.id))
            existing_ids = {row[0] for row in existing_ids_result.fetchall()}
            
            for qid, question_text, answer, node_id, difficulty in data["questions"]:
                if qid in existing_ids:
                    print(f"      ↷ {qid} already exists, skipping")
                    continue
                
                # Create database Question model
                db_question = QuestionModel(
                    id=qid,
                    text=question_text,
                    answer=answer,
                    options=None,
                    option_explanations=None,
                    question_type=QuestionType.OPEN.value,
                    knowledge_type=KnowledgeType.CONCEPT.value,
                    covered_node_ids=[node_id],
                    difficulty=difficulty,
                    tags=["fundamentals", project.id],
                    question_metadata={
                        "created_by": "system",
                        "created_at": (now - timedelta(days=difficulty)).isoformat(),
                        "importance": difficulty * 0.2,
                        "hits": 0,
                        "misses": 0,
                    },
                    last_attempted_at=now - timedelta(days=1) if difficulty > 1 else None,
                    source_material_ids=[]
                )
                
                session.add(db_question)
                print(f"      ✓ {qid}: {question_text[:40]}...")
            
            # Set community overrides for this project
            if data["community_overrides"]:
                for node_id, importance in data["community_overrides"].items():
                    community.set_node_importance(project.id, node_id, importance)
                print(f"    ✓ Set {len(data['community_overrides'])} community overrides")
        
        await session.commit()
    
    print("\n" + "="*60)
    print("✅ Database seeding complete!")
    print("="*60)
    print(f"\nCreated:")
    print(f"  • 1 user: {user.name}")
    print(f"  • {len(projects)} projects:")
    for p in projects:
        data = project_data[p.id]
        print(f"    - {p.name}: {len(data['nodes'])} nodes, {len(data['questions'])} questions")
    print(f"  • 1 community: {community.name}")
    print(f"    - Attached to {len(community.project_ids)} projects")
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
