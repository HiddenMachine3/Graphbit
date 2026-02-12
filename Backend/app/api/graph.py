"""Graph and knowledge node API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import EdgeType
from app.domain.material import Material, MaterialRegistry, MaterialType
from app.services.topic_extraction import extract_topics_from_text, TopicExtractionError
from app.services.video_transcripts import fetch_youtube_transcript
from app.db.session import get_db
from app.models import (
    Node as NodeModel,
    Edge as EdgeModel,
    Question as QuestionModel,
    AppUser as AppUserModel,
)

router = APIRouter()

class CreateNodeRequest(BaseModel):
    project_id: str
    topic_name: str
    importance: float = 0.5
    relevance: float = 0.5
    node_kind: Optional[str] = None


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


class BulkDeleteNodesRequest(BaseModel):
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


async def _edge_exists_any(
    db: AsyncSession,
    project_id: str,
    from_node_id: str,
    to_node_id: str,
) -> Optional[EdgeModel]:
    result = await db.execute(
        select(EdgeModel).where(
            EdgeModel.project_id == project_id,
            (
                (EdgeModel.source == from_node_id) & (EdgeModel.target == to_node_id)
                | (EdgeModel.source == to_node_id) & (EdgeModel.target == from_node_id)
            ),
        )
    )
    return result.scalar_one_or_none()


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

    question_counts: dict[str, int] = {}
    for question in questions:
        for node_id in question.covered_node_ids:
            question_counts[node_id] = question_counts.get(node_id, 0) + 1

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
            }
            for node in nodes
        ],
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
        ],
    }


async def _topic_is_shared(
    db: AsyncSession,
    project_id: str,
    topic_id: str,
    chapter_id: str,
) -> bool:
    result = await db.execute(
        select(EdgeModel.id).where(
            EdgeModel.project_id == project_id,
            EdgeModel.target == topic_id,
            EdgeModel.type == EdgeType.SUBCONCEPT_OF.value,
            EdgeModel.source != chapter_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _collect_cascade_nodes(
    db: AsyncSession,
    project_id: str,
    chapter_id: str,
) -> list[str]:
    result = await db.execute(
        select(EdgeModel.target).where(
            EdgeModel.project_id == project_id,
            EdgeModel.source == chapter_id,
            EdgeModel.type == EdgeType.SUBCONCEPT_OF.value,
        )
    )
    topic_ids = [row[0] for row in result.fetchall()]

    deletable = [chapter_id]
    for topic_id in topic_ids:
        if not await _topic_is_shared(db, project_id, topic_id, chapter_id):
            deletable.append(topic_id)
    return deletable


async def _remove_nodes_and_edges(
    db: AsyncSession,
    project_id: str,
    node_ids: list[str],
) -> dict:
    if not node_ids:
        return {
            "deleted_node_ids": [],
            "deleted_edge_ids": [],
            "updated_questions": 0,
            "deleted_questions": 0,
        }

    edges_result = await db.execute(
        select(EdgeModel).where(
            EdgeModel.project_id == project_id,
            (EdgeModel.source.in_(node_ids)) | (EdgeModel.target.in_(node_ids)),
        )
    )
    edges = edges_result.scalars().all()
    deleted_edge_ids = [edge.id for edge in edges]
    for edge in edges:
        await db.delete(edge)

    nodes_result = await db.execute(
        select(NodeModel).where(
            NodeModel.project_id == project_id,
            NodeModel.id.in_(node_ids),
        )
    )
    nodes = nodes_result.scalars().all()
    deleted_node_ids = [node.id for node in nodes]
    for node in nodes:
        await db.delete(node)

    questions_result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    questions = questions_result.scalars().all()

    updated_questions = 0
    deleted_questions = 0
    delete_set = set(node_ids)
    for question in questions:
        covered = list(question.covered_node_ids or [])
        filtered = [node_id for node_id in covered if node_id not in delete_set]
        if filtered == covered:
            continue
        if not filtered:
            await db.delete(question)
            deleted_questions += 1
        else:
            question.covered_node_ids = filtered
            updated_questions += 1

    return {
        "deleted_node_ids": deleted_node_ids,
        "deleted_edge_ids": deleted_edge_ids,
        "updated_questions": updated_questions,
        "deleted_questions": deleted_questions,
    }


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


def _get_or_create_material(video_url: str, title: str, channel: Optional[str], project_id: str = "") -> Material:
    global _material_counter

    existing_id = _material_index_by_source.get(video_url)
    if existing_id and _material_registry.has_material(existing_id):
        return _material_registry.get_material(existing_id)

    _material_counter += 1
    material_id = f"material-{_material_counter}"
    material = Material(
        id=material_id,
        project_id=project_id,
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
        created_by="system",
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
        created_by="system",
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
    node_kind = (request.node_kind or "topic").lower()
    node_prefix = "chapter" if node_kind == "chapter" else "node"
    node_id = f"{node_prefix}_{int(datetime.now().timestamp() * 1000)}"
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


@router.delete("/graph/nodes/{node_id}")
async def delete_node(
    node_id: str,
    project_id: str = Query(...),
    mode: str = Query("single"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a node. Use mode=cascade to remove connected topic nodes for a chapter."""
    node_result = await db.execute(
        select(NodeModel).where(
            NodeModel.project_id == project_id,
            NodeModel.id == node_id,
        )
    )
    node = node_result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    mode_value = mode.lower()
    if mode_value == "cascade":
        node_ids = await _collect_cascade_nodes(db, project_id, node_id)
    else:
        node_ids = [node_id]

    result = await _remove_nodes_and_edges(db, project_id, node_ids)
    await db.commit()
    return result


@router.post("/graph/nodes/bulk-delete")
async def bulk_delete_nodes(
    request: BulkDeleteNodesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple nodes at once (non-cascade)."""
    unique_ids = [node_id for node_id in dict.fromkeys(request.node_ids) if node_id]
    result = await _remove_nodes_and_edges(db, request.project_id, unique_ids)
    await db.commit()
    return result


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

    existing_edge = await _edge_exists_any(
        db, request.project_id, request.from_node_id, request.to_node_id
    )
    if existing_edge:
        return {
            "id": existing_edge.id,
            "project_id": existing_edge.project_id,
            "source": existing_edge.source,
            "target": existing_edge.target,
            "type": existing_edge.type,
            "weight": existing_edge.weight,
        }
    
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


@router.delete("/graph/edges/{edge_id}")
async def delete_edge(
    edge_id: str,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Delete a connection between nodes."""
    result = await db.execute(
        select(EdgeModel).where(
            EdgeModel.project_id == project_id,
            EdgeModel.id == edge_id,
        )
    )
    edge = result.scalar_one_or_none()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")

    await db.delete(edge)
    await db.commit()
    return {"deleted_edge_id": edge_id}


@router.post("/graph/ingest/video")
async def ingest_video(request: VideoIngestRequest, db: AsyncSession = Depends(get_db)):
    """Ingest a video transcript, extract topics, and merge into the graph."""
    if not request.video_url.strip():
        raise HTTPException(status_code=400, detail="video_url is required")
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    transcript = request.transcript
    if not transcript:
        try:
            transcript = fetch_youtube_transcript(request.video_url)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch transcript: {exc}",
            )

    try:
        topics = request.topics or extract_topics_from_text(transcript, title=request.title)
    except TopicExtractionError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )
    topics = [topic.strip() for topic in topics if topic.strip()]

    if not topics:
        raise HTTPException(status_code=400, detail="No topics extracted")

    material = _get_or_create_material(request.video_url, request.title, request.channel, project_id=request.project_id)

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
