"""Graph and knowledge node API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domain import (
    Edge,
    EdgeType,
    Graph,
    KnowledgeType,
    Node,
    Question,
    QuestionMetadata,
    QuestionType,
)
from app.domain.material import Material, MaterialRegistry, MaterialType
from app.services.topic_extraction import extract_topics_from_text
from app.services.video_transcripts import fetch_youtube_transcript

router = APIRouter()

# Default project ID for demo/development
DEFAULT_PROJECT_ID = "demo_project"


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


class VideoIngestRequest(BaseModel):
    video_url: str
    title: str
    transcript: Optional[str] = None
    channel: Optional[str] = None
    topics: Optional[list[str]] = None


# In-memory storage for demo (replace with database queries)
_graph = Graph(project_id=DEFAULT_PROJECT_ID)
_questions = {}
_node_counter = 0
_material_counter = 0
_material_registry = MaterialRegistry()
_material_index_by_source: dict[str, str] = {}
_topic_index_by_key: dict[str, str] = {}
_chapter_index_by_source: dict[str, str] = {}
_topic_chapter_index: dict[str, set[str]] = {}

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
            project_id=DEFAULT_PROJECT_ID,
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
                project_id=DEFAULT_PROJECT_ID,
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
            project_id=DEFAULT_PROJECT_ID,
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


def _normalize_topic_key(topic_name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in topic_name)
    return " ".join(cleaned.split())


def _topic_id_from_key(topic_key: str) -> str:
    return "topic_" + topic_key.replace(" ", "_")[:48]


def _edge_exists(from_node_id: str, to_node_id: str, edge_type: EdgeType) -> bool:
    return any(
        edge.from_node_id == from_node_id
        and edge.to_node_id == to_node_id
        and edge.type == edge_type
        for edge in _graph.edges
    )


def _serialize_graph_summary():
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
                "linked_questions_count": sum(
                    1 for q in _questions.values() if node.id in q.covered_node_ids
                ),
                "linked_materials_count": len(node.source_material_ids),
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


def _get_or_create_material(video_url: str, title: str, channel: Optional[str]) -> Material:
    global _material_counter

    existing_id = _material_index_by_source.get(video_url)
    if existing_id and _material_registry.has_material(existing_id):
        return _material_registry.get_material(existing_id)

    _material_counter += 1
    material_id = f"material-{_material_counter}"
    material = Material(
        id=material_id,
        title=title,
        material_type=MaterialType.VIDEO,
        source=video_url,
        created_at=datetime.now(),
        metadata={"channel": channel or ""},
    )
    _material_registry.add_material(material)
    _material_index_by_source[video_url] = material_id
    return material


def _get_or_create_chapter_node(
    material: Material,
    title: str,
    video_url: str,
) -> str:
    existing = _chapter_index_by_source.get(video_url)
    if existing and existing in _graph.nodes:
        return existing

    chapter_id = f"chapter_{len(_chapter_index_by_source) + 1}"
    chapter_node = Node(
        id=chapter_id,
        project_id=DEFAULT_PROJECT_ID,
        topic_name=title,
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=0.9,
        relevance=1.0,
        view_frequency=1,
        source_material_ids={material.id},
    )
    _graph.add_node(chapter_node)
    _chapter_index_by_source[video_url] = chapter_id
    return chapter_id


def _get_or_create_topic_node(topic_name: str, material_id: str) -> str:
    topic_key = _normalize_topic_key(topic_name)
    if not topic_key:
        raise ValueError("Topic name cannot be empty")

    existing_id = _topic_index_by_key.get(topic_key)
    if existing_id and existing_id in _graph.nodes:
        _graph.nodes[existing_id].source_material_ids.add(material_id)
        return existing_id

    node_id = _topic_id_from_key(topic_key)
    if node_id in _graph.nodes:
        node_id = f"{node_id}_{len(_graph.nodes)}"

    node = Node(
        id=node_id,
        project_id=DEFAULT_PROJECT_ID,
        topic_name=topic_name.strip(),
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=0.6,
        relevance=0.9,
        view_frequency=0,
        source_material_ids={material_id},
    )
    _graph.add_node(node)
    _topic_index_by_key[topic_key] = node_id
    return node_id


@router.get("/graph")
async def get_graph_summary():
    """Get complete knowledge graph summary with nodes and edges."""
    return _serialize_graph_summary()


@router.get("/graph/nodes")
async def list_nodes():
    """List all knowledge nodes."""
    return _serialize_graph_summary()["nodes"]


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
        project_id=DEFAULT_PROJECT_ID,
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
        "linked_materials_count": len(node.source_material_ids),
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
        "linked_materials_count": len(node.source_material_ids),
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

    if _edge_exists(request.from_node_id, request.to_node_id, edge_type):
        return {
            "id": f"{request.from_node_id}-{request.to_node_id}",
            "source": request.from_node_id,
            "target": request.to_node_id,
            "type": edge_type.value,
            "weight": request.weight,
        }
    
    edge = Edge(
        from_node_id=request.from_node_id,
        to_node_id=request.to_node_id,
        project_id=DEFAULT_PROJECT_ID,
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


@router.post("/graph/ingest/video")
async def ingest_video(request: VideoIngestRequest):
    """Ingest a video transcript, extract topics, and merge into the graph."""
    if not request.video_url.strip():
        raise HTTPException(status_code=400, detail="video_url is required")
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    transcript = request.transcript
    if not transcript:
        transcript = fetch_youtube_transcript(request.video_url)

    topics = request.topics or extract_topics_from_text(transcript, title=request.title)
    topics = [topic.strip() for topic in topics if topic.strip()]

    if not topics:
        raise HTTPException(status_code=400, detail="No topics extracted")

    material = _get_or_create_material(request.video_url, request.title, request.channel)

    chapter_created = request.video_url not in _chapter_index_by_source
    chapter_node_id = _get_or_create_chapter_node(material, request.title, request.video_url)

    topics_result = []
    edges_added = 0

    for topic in topics:
        topic_key = _normalize_topic_key(topic)
        existing_topic_id = _topic_index_by_key.get(topic_key)
        topic_node_id = _get_or_create_topic_node(topic, material.id)

        if not _edge_exists(chapter_node_id, topic_node_id, EdgeType.SUBCONCEPT_OF):
            edge = Edge(
                from_node_id=chapter_node_id,
                to_node_id=topic_node_id,
                project_id=DEFAULT_PROJECT_ID,
                type=EdgeType.SUBCONCEPT_OF,
                weight=0.9,
            )
            _graph.add_edge(edge)
            edges_added += 1

        chapter_neighbors = _topic_chapter_index.get(topic_node_id, set())
        for other_chapter_id in sorted(chapter_neighbors):
            if other_chapter_id == chapter_node_id:
                continue
            if not _edge_exists(other_chapter_id, chapter_node_id, EdgeType.APPLIED_WITH):
                edge = Edge(
                    from_node_id=other_chapter_id,
                    to_node_id=chapter_node_id,
                    project_id=DEFAULT_PROJECT_ID,
                    type=EdgeType.APPLIED_WITH,
                    weight=0.4,
                )
                _graph.add_edge(edge)
                edges_added += 1

        _topic_chapter_index.setdefault(topic_node_id, set()).add(chapter_node_id)

        topics_result.append(
            {
                "topic": topic,
                "node_id": topic_node_id,
                "created": existing_topic_id is None,
            }
        )

    return {
        "chapter_node_id": chapter_node_id,
        "chapter_created": chapter_created,
        "topics": topics_result,
        "edges_added": edges_added,
        "graph": _serialize_graph_summary(),
    }
