"""Graph and knowledge node API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.domain import Node, Graph, Edge, EdgeType, Question, QuestionMetadata, QuestionType, KnowledgeType
from datetime import datetime
from typing import Optional

router = APIRouter()


class CreateNodeRequest(BaseModel):
    topic_name: str
    importance: float = 0.5
    relevance: float = 0.5


class UpdateNodeRequest(BaseModel):
    topic_name: Optional[str] = None
    proven_knowledge_rating: Optional[float] = None
    user_estimated_knowledge_rating: Optional[float] = None
    importance: Optional[float] = None
    relevance: Optional[float] = None


class CreateEdgeRequest(BaseModel):
    from_node_id: str
    to_node_id: str
    edge_type: str = "PREREQUISITE"
    weight: float = 1.0


# In-memory storage for demo (replace with database queries)
_graph = Graph()
_questions = {}
_node_counter = 0

# Initialize with sample data
def _init_sample_data():
    """Initialize with sample data."""
    global _graph, _questions
    
    # Create nodes
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
        _graph.add_node(node)
    
    # Create edges (connections between topics)
    edges_data = [
        ("python_basics", "variables", EdgeType.PREREQUISITE, 1.0),
        ("variables", "functions", EdgeType.PREREQUISITE, 1.0),
        ("functions", "oop", EdgeType.PREREQUISITE, 1.0),
        ("oop", "classes", EdgeType.PREREQUISITE, 1.0),
        ("classes", "inheritance", EdgeType.PREREQUISITE, 1.0),
        ("classes", "decorators", EdgeType.APPLIED_WITH, 0.7),
        ("functions", "async", EdgeType.APPLIED_WITH, 0.8),
        ("python_basics", "functions", EdgeType.APPLIED_WITH, 0.6),
        ("oop", "inheritance", EdgeType.PREREQUISITE, 0.9),
        ("inheritance", "polymorphism", EdgeType.APPLIED_WITH, 0.8),
    ]
    
    for from_id, to_id, edge_type, weight in edges_data:
        # Only create edge if both nodes exist
        if from_id in _graph.nodes and to_id in _graph.nodes:
            edge = Edge(
                from_node_id=from_id,
                to_node_id=to_id,
                type=edge_type,
                weight=weight
            )
            _graph.add_edge(edge)
    
    # Create questions
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
                created_at=now,
                importance=difficulty * 0.2
            ),
            difficulty=difficulty,
            tags={"fundamentals", "python"},
        )
        _questions[qid] = question


# Initialize on module load
_init_sample_data()


@router.get("/graph")
async def get_graph_summary():
    """Get complete knowledge graph summary with nodes and edges."""
    return {
        "nodes": [
            {
                "id": node.id,
                "topic_name": node.topic_name,
                "proven_knowledge_rating": node.proven_knowledge_rating,
                "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
                "importance": node.importance,
                "relevance": node.relevance,
                "view_frequency": node.view_frequency,
                "source_material_ids": list(node.source_material_ids),
                "forgetting_score": 1.0 - node.proven_knowledge_rating,
                "linked_questions_count": sum(1 for q in _questions.values() if node.id in q.covered_node_ids),
                "linked_materials_count": 0,
            }
            for node in _graph.nodes.values()
        ],
        "edges": [
            {
                "id": f"{edge.from_node_id}-{edge.to_node_id}",
                "source": edge.from_node_id,
                "target": edge.to_node_id,
                "type": edge.type.value,
                "weight": edge.weight,
            }
            for edge in _graph.edges
        ],
    }


@router.get("/graph/nodes")
async def list_nodes():
    """List all knowledge nodes."""
    return [
        {
            "id": node.id,
            "topic_name": node.topic_name,
            "proven_knowledge_rating": node.proven_knowledge_rating,
            "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
            "importance": node.importance,
            "relevance": node.relevance,
            "view_frequency": node.view_frequency,
            "source_material_ids": list(node.source_material_ids),
            "forgetting_score": 1.0 - node.proven_knowledge_rating,
            "linked_questions_count": sum(1 for q in _questions.values() if node.id in q.covered_node_ids),
            "linked_materials_count": 0,
        }
        for node in _graph.nodes.values()
    ]


@router.get("/graph/questions")
async def list_questions():
    """List all questions."""
    return [
        {
            "id": q.id,
            "text": q.text,
            "answer": q.answer,
            "question_type": q.question_type.value,
            "knowledge_type": q.knowledge_type.value,
            "covered_node_ids": q.covered_node_ids,
            "metadata": {
                "created_by": q.metadata.created_by,
                "created_at": q.metadata.created_at.isoformat(),
                "importance": q.metadata.importance,
                "hits": q.metadata.hits,
                "misses": q.metadata.misses,
            },
            "difficulty": q.difficulty,
            "tags": list(q.tags),
            "last_attempted_at": q.last_attempted_at.isoformat() if q.last_attempted_at else None,
            "source_material_ids": list(q.source_material_ids),
        }
        for q in _questions.values()
    ]


@router.post("/graph/nodes")
async def create_node(request: CreateNodeRequest):
    """Create a new knowledge node."""
    global _node_counter
    _node_counter += 1
    
    node_id = f"node_{_node_counter}"
    node = Node(
        id=node_id,
        topic_name=request.topic_name,
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=request.importance,
        relevance=request.relevance,
        view_frequency=0
    )
    _graph.add_node(node)
    
    return {
        "id": node.id,
        "topic_name": node.topic_name,
        "proven_knowledge_rating": node.proven_knowledge_rating,
        "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
        "importance": node.importance,
        "relevance": node.relevance,
        "view_frequency": node.view_frequency,
        "source_material_ids": list(node.source_material_ids),
        "forgetting_score": 1.0 - node.proven_knowledge_rating,
        "linked_questions_count": 0,
        "linked_materials_count": 0,
    }


@router.put("/graph/nodes/{node_id}")
async def update_node(node_id: str, request: UpdateNodeRequest):
    """Update node properties."""
    if node_id not in _graph.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node = _graph.nodes[node_id]
    
    if request.topic_name is not None:
        node.topic_name = request.topic_name
    if request.proven_knowledge_rating is not None:
        node.proven_knowledge_rating = request.proven_knowledge_rating
    if request.user_estimated_knowledge_rating is not None:
        node.user_estimated_knowledge_rating = request.user_estimated_knowledge_rating
    if request.importance is not None:
        node.importance = request.importance
    if request.relevance is not None:
        node.relevance = request.relevance
    
    return {
        "id": node.id,
        "topic_name": node.topic_name,
        "proven_knowledge_rating": node.proven_knowledge_rating,
        "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
        "importance": node.importance,
        "relevance": node.relevance,
        "view_frequency": node.view_frequency,
        "source_material_ids": list(node.source_material_ids),
        "forgetting_score": 1.0 - node.proven_knowledge_rating,
        "linked_questions_count": sum(1 for q in _questions.values() if node_id in q.covered_node_ids),
        "linked_materials_count": 0,
    }


@router.post("/graph/edges")
async def create_edge(request: CreateEdgeRequest):
    """Create a new connection between nodes."""
    if request.from_node_id not in _graph.nodes:
        raise HTTPException(status_code=404, detail="From node not found")
    if request.to_node_id not in _graph.nodes:
        raise HTTPException(status_code=404, detail="To node not found")
    
    # Map string to EdgeType
    edge_type_map = {
        "PREREQUISITE": EdgeType.PREREQUISITE,
        "DEPENDS_ON": EdgeType.DEPENDS_ON,
        "APPLIED_WITH": EdgeType.APPLIED_WITH,
        "SUBCONCEPT_OF": EdgeType.SUBCONCEPT_OF,
    }
    edge_type = edge_type_map.get(request.edge_type, EdgeType.PREREQUISITE)
    
    edge = Edge(
        from_node_id=request.from_node_id,
        to_node_id=request.to_node_id,
        type=edge_type,
        weight=request.weight
    )
    _graph.add_edge(edge)
    
    return {
        "id": f"{edge.from_node_id}-{edge.to_node_id}",
        "source": edge.from_node_id,
        "target": edge.to_node_id,
        "type": edge.type.value,
        "weight": edge.weight,
    }
