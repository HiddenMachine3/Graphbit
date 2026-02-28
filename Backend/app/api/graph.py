"""Graph and knowledge node API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import EdgeType
from app.domain.material import Material, MaterialRegistry, MaterialType
from app.services.topic_extraction import extract_topics_from_text
from app.services.video_transcripts import fetch_youtube_transcript
from app.db.session import get_db
from app.models import (
    Node as NodeModel,
    Edge as EdgeModel,
    Question as QuestionModel,
    Material as MaterialModel,
    AppUser as AppUserModel,
)

router = APIRouter()

class CreateNodeRequest(BaseModel):
    project_id: str
    topic_name: str
    importance: float = 0.0
    relevance: float = 0.5


class UpdateNodeRequest(BaseModel):
    project_id: str
    topic_name: Optional[str] = None
    proven_knowledge_rating: Optional[float] = None
    user_estimated_knowledge_rating: Optional[float] = None
    importance: Optional[float] = None
    relevance: Optional[float] = None


class CreateEdgeRequest(BaseModel):
    project_id: str
    from_node_id: str
    to_node_id: str
    edge_type: str = "PREREQUISITE"
    weight: float = 1.0


class DeleteNodesRequest(BaseModel):
    project_id: str
    node_ids: list[str]


class VideoIngestRequest(BaseModel):
    project_id: str
    video_url: str
    title: str
    transcript: Optional[str] = None
    channel: Optional[str] = None
    topics: Optional[list[str]] = None


# In-memory storage for materials and ingest indexes
_material_counter = 0
_material_registry = MaterialRegistry()
_material_index_by_source: dict[str, str] = {}
_topic_index_by_key: dict[tuple[str, str], str] = {}
_chapter_index_by_source: dict[tuple[str, str], str] = {}
_topic_chapter_index: dict[tuple[str, str], set[str]] = {}


def _normalize_topic_key(topic_name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in topic_name)
    return " ".join(cleaned.split())


def _topic_id_from_key(topic_key: str) -> str:
    return "topic_" + topic_key.replace(" ", "_")[:48]


async def _edge_exists(
    db: AsyncSession,
    project_id: str,
    from_node_id: str,
    to_node_id: str,
    edge_type: EdgeType,
) -> bool:
    result = await db.execute(
        select(EdgeModel.id).where(
            EdgeModel.project_id == project_id,
            EdgeModel.source == from_node_id,
            EdgeModel.target == to_node_id,
            EdgeModel.type == edge_type.value,
        )
    )
    return result.scalar_one_or_none() is not None


async def _serialize_graph_summary(project_id: str, db: AsyncSession):
    nodes_result = await db.execute(
        select(NodeModel).where(NodeModel.project_id == project_id)
    )
    nodes = nodes_result.scalars().all()

    edges_result = await db.execute(
        select(EdgeModel).where(EdgeModel.project_id == project_id)
    )
    edges = edges_result.scalars().all()

    questions_result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    questions = questions_result.scalars().all()

    materials_result = await db.execute(
        select(MaterialModel).where(MaterialModel.project_id == project_id)
    )
    materials = materials_result.scalars().all()

    question_counts: dict[str, int] = {}
    for question in questions:
        for node_id in question.covered_node_ids:
            question_counts[node_id] = question_counts.get(node_id, 0) + 1

    material_links: dict[str, set[str]] = {}
    for node in nodes:
        for material_id in node.source_material_ids or []:
            material_links.setdefault(material_id, set()).add(node.id)

    for question in questions:
        if not question.covered_node_ids:
            continue
        for material_id in question.source_material_ids or []:
            linked_nodes = material_links.setdefault(material_id, set())
            for node_id in question.covered_node_ids:
                linked_nodes.add(node_id)

    material_nodes = []
    material_edges = []
    for material in materials:
        linked_nodes = material_links.get(material.id, set())
        if not linked_nodes:
            continue

        material_node_id = f"material:{material.id}"
        material_nodes.append(
            {
                "id": material_node_id,
                "project_id": material.project_id,
                "created_by": material.created_by,
                "topic_name": material.title,
                "proven_knowledge_rating": 0.05,
                "user_estimated_knowledge_rating": 0.05,
                "importance": 1.0,
                "relevance": 1.0,
                "view_frequency": 1,
                "source_material_ids": [material.id],
                "forgetting_score": 0.95,
                "linked_questions_count": 0,
                "linked_materials_count": 0,
                "node_type": "material",
            }
        )

        for node_id in sorted(linked_nodes):
            material_edges.append(
                {
                    "id": f"{material_node_id}-node:{node_id}-MATERIAL",
                    "project_id": material.project_id,
                    "source": material_node_id,
                    "target": node_id,
                    "type": "MATERIAL",
                    "weight": 0.8,
                }
            )

    return {
        "nodes": [
            {
                "id": node.id,
                "project_id": node.project_id,
                "created_by": node.created_by,
                "topic_name": node.topic_name,
                "proven_knowledge_rating": node.proven_knowledge_rating,
                "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
                "importance": node.importance,
                "relevance": node.relevance,
                "view_frequency": node.view_frequency,
                "source_material_ids": list(node.source_material_ids or []),
                "forgetting_score": 1.0 - node.proven_knowledge_rating,
                "linked_questions_count": question_counts.get(node.id, 0),
                "linked_materials_count": len(node.source_material_ids or []),
                "node_type": "topic",
            }
            for node in nodes
        ] + material_nodes,
        "edges": [
            {
                "id": edge.id,
                "project_id": edge.project_id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.type,
                "weight": edge.weight,
            }
            for edge in edges
        ] + material_edges,
    }


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


async def _update_node_search_vector(db: AsyncSession, node_id: str) -> None:
    if db.bind.dialect.name != "postgresql":
        return
    await db.execute(
        text(
            "UPDATE nodes "
            "SET search_vector = to_tsvector('english', COALESCE(topic_name, '')) "
            "WHERE id = :node_id"
        ),
        {"node_id": node_id},
    )


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


async def _get_or_create_chapter_node(
    db: AsyncSession,
    project_id: str,
    material: Material,
    title: str,
    video_url: str,
) -> str:
    index_key = (project_id, video_url)
    existing = _chapter_index_by_source.get(index_key)
    if existing:
        result = await db.execute(
            select(NodeModel.id).where(
                NodeModel.project_id == project_id,
                NodeModel.id == existing,
            )
        )
        if result.scalar_one_or_none():
            return existing

    chapter_id = f"chapter_{len(_chapter_index_by_source) + 1}"
    chapter_node = NodeModel(
        id=chapter_id,
        project_id=project_id,
        topic_name=title,
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=0.9,
        relevance=1.0,
        view_frequency=1,
        source_material_ids=[material.id],
    )
    db.add(chapter_node)
    await db.flush()
    _chapter_index_by_source[index_key] = chapter_id
    return chapter_id


async def _get_or_create_topic_node(
    db: AsyncSession,
    project_id: str,
    topic_name: str,
    material_id: str,
) -> str:
    topic_key = _normalize_topic_key(topic_name)
    if not topic_key:
        raise ValueError("Topic name cannot be empty")

    index_key = (project_id, topic_key)
    existing_id = _topic_index_by_key.get(index_key)
    if existing_id:
        result = await db.execute(
            select(NodeModel).where(
                NodeModel.project_id == project_id,
                NodeModel.id == existing_id,
            )
        )
        existing_node = result.scalar_one_or_none()
        if existing_node:
            source_ids = set(existing_node.source_material_ids or [])
            source_ids.add(material_id)
            existing_node.source_material_ids = list(source_ids)
            return existing_id

    node_id = _topic_id_from_key(topic_key)

    node = NodeModel(
        id=node_id,
        project_id=project_id,
        topic_name=topic_name.strip(),
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=0.6,
        relevance=0.9,
        view_frequency=0,
        source_material_ids=[material_id],
    )
    db.add(node)
    await db.flush()
    _topic_index_by_key[index_key] = node_id
    return node_id


@router.get("/graph")
async def get_graph_summary(
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Get complete knowledge graph summary with nodes and edges."""
    return await _serialize_graph_summary(project_id, db)


@router.get("/graph/nodes")
async def list_nodes(
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge nodes."""
    summary = await _serialize_graph_summary(project_id, db)
    return summary["nodes"]


@router.get("/graph/questions")
async def list_questions(
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """List all questions."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    questions = result.scalars().all()
    return [
        {
            "id": q.id,
            "project_id": q.project_id,
            "text": q.text,
            "answer": q.answer,
            "question_type": q.question_type,
            "knowledge_type": q.knowledge_type,
            "covered_node_ids": q.covered_node_ids,
            "metadata": q.question_metadata,
            "difficulty": q.difficulty,
            "tags": q.tags,
            "last_attempted_at": q.last_attempted_at.isoformat() if q.last_attempted_at else None,
            "source_material_ids": q.source_material_ids,
        }
        for q in questions
    ]


@router.post("/graph/nodes")
async def create_node(request: CreateNodeRequest, db: AsyncSession = Depends(get_db)):
    """Create a new knowledge node."""
    node_id = f"node_{int(datetime.now().timestamp() * 1000)}"
    default_user = await _get_default_user(db)
    created_by = default_user.username if default_user else ""
    node = NodeModel(
        id=node_id,
        project_id=request.project_id,
        created_by=created_by,
        topic_name=request.topic_name,
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=request.importance,
        relevance=request.relevance,
        view_frequency=0,
        source_material_ids=[],
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    await _update_node_search_vector(db, node.id)
    
    return {
        "id": node.id,
        "project_id": node.project_id,
        "created_by": node.created_by,
        "topic_name": node.topic_name,
        "proven_knowledge_rating": node.proven_knowledge_rating,
        "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
        "importance": node.importance,
        "relevance": node.relevance,
        "view_frequency": node.view_frequency,
        "source_material_ids": list(node.source_material_ids or []),
        "forgetting_score": 1.0 - node.proven_knowledge_rating,
        "linked_questions_count": 0,
        "linked_materials_count": len(node.source_material_ids or []),
    }


@router.put("/graph/nodes/{node_id}")
async def update_node(
    node_id: str,
    request: UpdateNodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update node properties."""
    result = await db.execute(
        select(NodeModel).where(
            NodeModel.project_id == request.project_id,
            NodeModel.id == node_id,
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
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
    
    await db.commit()
    await db.refresh(node)
    await _update_node_search_vector(db, node.id)

    result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == request.project_id)
    )
    questions = result.scalars().all()
    linked_questions_count = sum(
        1 for q in questions if node_id in q.covered_node_ids
    )

    return {
        "id": node.id,
        "project_id": node.project_id,
        "created_by": node.created_by,
        "topic_name": node.topic_name,
        "proven_knowledge_rating": node.proven_knowledge_rating,
        "user_estimated_knowledge_rating": node.user_estimated_knowledge_rating,
        "importance": node.importance,
        "relevance": node.relevance,
        "view_frequency": node.view_frequency,
        "source_material_ids": list(node.source_material_ids or []),
        "forgetting_score": 1.0 - node.proven_knowledge_rating,
        "linked_questions_count": linked_questions_count,
        "linked_materials_count": len(node.source_material_ids or []),
    }


@router.post("/graph/edges")
async def create_edge(request: CreateEdgeRequest, db: AsyncSession = Depends(get_db)):
    """Create a new connection between nodes."""
    from_node = await db.execute(
        select(NodeModel.id).where(
            NodeModel.project_id == request.project_id,
            NodeModel.id == request.from_node_id,
        )
    )
    if from_node.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="From node not found")

    to_node = await db.execute(
        select(NodeModel.id).where(
            NodeModel.project_id == request.project_id,
            NodeModel.id == request.to_node_id,
        )
    )
    if to_node.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="To node not found")
    
    # Map string to EdgeType
    edge_type_map = {
        "PREREQUISITE": EdgeType.PREREQUISITE,
        "DEPENDS_ON": EdgeType.DEPENDS_ON,
        "APPLIED_WITH": EdgeType.APPLIED_WITH,
        "SUBCONCEPT_OF": EdgeType.SUBCONCEPT_OF,
    }
    edge_type = edge_type_map.get(request.edge_type, EdgeType.PREREQUISITE)

    if await _edge_exists(db, request.project_id, request.from_node_id, request.to_node_id, edge_type):
        return {
            "id": f"{request.from_node_id}-{request.to_node_id}-{edge_type.value}",
            "project_id": request.project_id,
            "source": request.from_node_id,
            "target": request.to_node_id,
            "type": edge_type.value,
            "weight": request.weight,
        }
    
    edge_id = f"{request.from_node_id}-{request.to_node_id}-{edge_type.value}"
    edge = EdgeModel(
        id=edge_id,
        project_id=request.project_id,
        source=request.from_node_id,
        target=request.to_node_id,
        type=edge_type.value,
        weight=request.weight,
    )
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    
    return {
        "id": edge.id,
        "project_id": edge.project_id,
        "source": edge.source,
        "target": edge.target,
        "type": edge.type,
        "weight": edge.weight,
    }


@router.delete("/graph/nodes/{node_id}")
async def delete_node(
    node_id: str,
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Delete a node and its connected edges."""
    if node_id.startswith("material:"):
        raise HTTPException(status_code=400, detail="Material nodes cannot be deleted")

    result = await db.execute(
        select(NodeModel).where(
            NodeModel.project_id == project_id,
            NodeModel.id == node_id,
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    await db.execute(
        delete(EdgeModel).where(
            EdgeModel.project_id == project_id,
            or_(EdgeModel.source == node_id, EdgeModel.target == node_id),
        )
    )

    questions_result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    questions = questions_result.scalars().all()
    updated_questions = 0
    for question in questions:
        if not question.covered_node_ids:
            continue
        if node_id in question.covered_node_ids:
            question.covered_node_ids = [
                existing_id for existing_id in question.covered_node_ids if existing_id != node_id
            ]
            updated_questions += 1

    await db.delete(node)
    await db.commit()

    return {
        "deleted": [node_id],
        "updated_questions": updated_questions,
    }


@router.post("/graph/nodes/bulk-delete")
async def bulk_delete_nodes(request: DeleteNodesRequest, db: AsyncSession = Depends(get_db)):
    """Delete multiple nodes and their connected edges."""
    node_ids = [node_id for node_id in request.node_ids if node_id]
    if not node_ids:
        raise HTTPException(status_code=400, detail="node_ids cannot be empty")
    if any(node_id.startswith("material:") for node_id in node_ids):
        raise HTTPException(status_code=400, detail="Material nodes cannot be deleted")

    result = await db.execute(
        select(NodeModel).where(
            NodeModel.project_id == request.project_id,
            NodeModel.id.in_(node_ids),
        )
    )
    nodes = result.scalars().all()
    existing_ids = {node.id for node in nodes}
    missing = [node_id for node_id in node_ids if node_id not in existing_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Nodes not found: {', '.join(missing)}")

    await db.execute(
        delete(EdgeModel).where(
            EdgeModel.project_id == request.project_id,
            or_(EdgeModel.source.in_(node_ids), EdgeModel.target.in_(node_ids)),
        )
    )

    questions_result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == request.project_id)
    )
    questions = questions_result.scalars().all()
    updated_questions = 0
    node_id_set = set(node_ids)
    for question in questions:
        if not question.covered_node_ids:
            continue
        if any(node_id in node_id_set for node_id in question.covered_node_ids):
            question.covered_node_ids = [
                existing_id for existing_id in question.covered_node_ids if existing_id not in node_id_set
            ]
            updated_questions += 1

    await db.execute(
        delete(NodeModel).where(
            NodeModel.project_id == request.project_id,
            NodeModel.id.in_(node_ids),
        )
    )
    await db.commit()

    return {
        "deleted": node_ids,
        "updated_questions": updated_questions,
    }


@router.post("/graph/ingest/video")
async def ingest_video(request: VideoIngestRequest, db: AsyncSession = Depends(get_db)):
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
    chapter_node_id = await _get_or_create_chapter_node(
        db,
        request.project_id,
        material,
        request.title,
        request.video_url,
    )

    topics_result = []
    edges_added = 0

    for topic in topics:
        topic_key = _normalize_topic_key(topic)
        index_key = (request.project_id, topic_key)
        existing_topic_id = _topic_index_by_key.get(index_key)
        topic_node_id = await _get_or_create_topic_node(
            db,
            request.project_id,
            topic,
            material.id,
        )

        if not await _edge_exists(
            db,
            request.project_id,
            chapter_node_id,
            topic_node_id,
            EdgeType.SUBCONCEPT_OF,
        ):
            edge_id = f"{chapter_node_id}-{topic_node_id}-{EdgeType.SUBCONCEPT_OF.value}"
            edge = EdgeModel(
                id=edge_id,
                project_id=request.project_id,
                source=chapter_node_id,
                target=topic_node_id,
                type=EdgeType.SUBCONCEPT_OF.value,
                weight=0.9,
            )
            db.add(edge)
            edges_added += 1

        chapter_neighbors = _topic_chapter_index.get((request.project_id, topic_node_id), set())
        for other_chapter_id in sorted(chapter_neighbors):
            if other_chapter_id == chapter_node_id:
                continue
            if not await _edge_exists(
                db,
                request.project_id,
                other_chapter_id,
                chapter_node_id,
                EdgeType.APPLIED_WITH,
            ):
                edge_id = f"{other_chapter_id}-{chapter_node_id}-{EdgeType.APPLIED_WITH.value}"
                edge = EdgeModel(
                    id=edge_id,
                    project_id=request.project_id,
                    source=other_chapter_id,
                    target=chapter_node_id,
                    type=EdgeType.APPLIED_WITH.value,
                    weight=0.4,
                )
                db.add(edge)
                edges_added += 1

        _topic_chapter_index.setdefault((request.project_id, topic_node_id), set()).add(chapter_node_id)

        topics_result.append(
            {
                "topic": topic,
                "node_id": topic_node_id,
                "created": existing_topic_id is None,
            }
        )

    await db.commit()

    return {
        "chapter_node_id": chapter_node_id,
        "chapter_created": chapter_created,
        "topics": topics_result,
        "edges_added": edges_added,
        "graph": await _serialize_graph_summary(request.project_id, db),
    }
