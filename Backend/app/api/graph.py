"""Graph and knowledge node API endpoints."""

from datetime import datetime
from typing import Optional
import asyncio
import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import EdgeType
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
logger = logging.getLogger(__name__)

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
    material_id: Optional[str] = None
    include_chapter_node: bool = True


_topic_index_by_key: dict[tuple[str, str], str] = {}
_chapter_index_by_source: dict[tuple[str, str], str] = {}
_topic_chapter_index: dict[tuple[str, str], set[str]] = {}


def _normalize_topic_key(topic_name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in topic_name)
    return " ".join(cleaned.split())


def _topic_id_from_key(topic_key: str, project_id: str = "") -> str:
    slug = topic_key.replace(" ", "_")[:48]
    if project_id:
        # Include short hash of project_id for global PK uniqueness
        suffix = hashlib.md5(project_id.encode()).hexdigest()[:8]
        return f"topic_{slug}_{suffix}"
    return f"topic_{slug}"


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

    # Determine sequential order of chapter nodes for sequence_number
    chapter_nodes_sorted = sorted(
        [n for n in nodes if n.id.startswith("chapter_")],
        key=lambda n: n.created_at or datetime.min,
    )
    chapter_sequence_map: dict[str, int] = {
        n.id: i + 1 for i, n in enumerate(chapter_nodes_sorted)
    }

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
                "node_type": "chapter" if node.id.startswith("chapter_") else "topic",
                "sequence_number": chapter_sequence_map.get(node.id),
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
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id).limit(1))
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


async def _auto_generate_questions_for_node(
    project_id: str,
    node_id: str,
    topic_name: str,
    created_by: str,
    transcript_context: str = "",
    material_id: str = "",
):
    """Background task to auto-generate a mixed question bank for a topic node.
    
    Generates: 2 MCQ + 1 OPEN + 1 FLASHCARD = 4 questions per topic.
    Uses transcript context for content-aware questions when available.
    """
    try:
        from app.api.qa_generation import QAGenerationRequest, generate_qa_pairs
        from app.models import Question as QuestionModel
        from app.db.session import AsyncSessionLocal
        import uuid
        from datetime import datetime

        # Build content-aware prompt
        if transcript_context:
            context_text = (
                f"Topic: {topic_name}\n\n"
                f"The following is the actual lecture/video content covering this topic:\n"
                f"{transcript_context[:3000]}"  # Cap at 3000 chars per topic
            )
        else:
            context_text = f"Topic: {topic_name}. Generate questions that test deep understanding of this concept."

        # Dedup check: fetch existing questions for this node
        async with AsyncSessionLocal() as db:
            existing_result = await db.execute(
                select(QuestionModel).where(
                    QuestionModel.project_id == project_id,
                )
            )
            existing_questions = existing_result.scalars().all()
            existing_texts = set()
            for q in existing_questions:
                if node_id in (q.covered_node_ids or []):
                    existing_texts.add(q.text.strip().lower()[:80])

        source_mats = [material_id] if material_id else []
        generation_plan = [
            ("mcq", 2),
            ("open", 1),
            ("flashcard", 1),
        ]

        all_new_questions = []
        for q_type, count in generation_plan:
            try:
                request = QAGenerationRequest(text=context_text, n=count, question_type=q_type)
                response = await generate_qa_pairs(request)
                if not response or not response.qa_pairs:
                    continue

                for pair in response.qa_pairs:
                    # Dedup: skip if similar question already exists
                    q_text = (pair.question or "").strip()
                    if q_text.lower()[:80] in existing_texts:
                        continue
                    existing_texts.add(q_text.lower()[:80])

                    q_id = f"question-{uuid.uuid4().hex[:12]}"
                    all_new_questions.append(QuestionModel(
                        id=q_id,
                        project_id=project_id,
                        created_by=created_by,
                        text=q_text,
                        answer=pair.answer or "",
                        options=pair.options if hasattr(pair, 'options') else None,
                        option_explanations=None,
                        question_type=pair.question_type.upper(),
                        knowledge_type="CONCEPT",
                        covered_node_ids=[node_id],
                        difficulty=2,
                        tags=[topic_name],
                        question_metadata={
                            "created_by": created_by,
                            "created_at": datetime.now().isoformat(),
                            "importance": 0.5,
                            "hits": 0,
                            "misses": 0,
                            "review_interval_days": 1.0,
                            "auto_generated": True,
                        },
                        source_material_ids=source_mats,
                    ))
            except Exception as e:
                logger.warning("Failed to generate %s questions for node %s: %s", q_type, node_id, e)

        if all_new_questions:
            async with AsyncSessionLocal() as db:
                for q in all_new_questions:
                    db.add(q)
                await db.commit()
                logger.info(
                    "Auto-generated %d questions for topic node %s (%s): %s",
                    len(all_new_questions), node_id, topic_name,
                    ", ".join(q.question_type for q in all_new_questions),
                )
    except Exception as e:
        logger.error("Failed to auto-generate questions for node %s: %s", node_id, e)


async def _auto_generate_questions_for_chapter(
    project_id: str,
    chapter_node_id: str,
    chapter_title: str,
    created_by: str,
    transcript_text: str = "",
    material_id: str = "",
):
    """Background task to auto-generate questions for a chapter (video) node.
    
    Generates: 2 MCQ + 2 OPEN = 4 questions per chapter.
    Uses the full chapter transcript for deep, comprehensive questions.
    """
    try:
        from app.api.qa_generation import QAGenerationRequest, generate_qa_pairs
        from app.models import Question as QuestionModel
        from app.db.session import AsyncSessionLocal
        import uuid
        from datetime import datetime

        if transcript_text:
            context_text = (
                f"Video/Chapter: {chapter_title}\n\n"
                f"Full transcript of this chapter:\n"
                f"{transcript_text[:4000]}"  # Cap at 4000 chars for chapters
            )
        else:
            context_text = f"Chapter: {chapter_title}. Generate comprehensive questions covering the key concepts of this chapter."

        source_mats = [material_id] if material_id else []
        generation_plan = [
            ("mcq", 2),
            ("open", 2),
        ]

        all_new_questions = []
        for q_type, count in generation_plan:
            try:
                request = QAGenerationRequest(text=context_text, n=count, question_type=q_type)
                response = await generate_qa_pairs(request)
                if not response or not response.qa_pairs:
                    continue

                for pair in response.qa_pairs:
                    q_id = f"question-{uuid.uuid4().hex[:12]}"
                    all_new_questions.append(QuestionModel(
                        id=q_id,
                        project_id=project_id,
                        created_by=created_by,
                        text=(pair.question or "").strip(),
                        answer=pair.answer or "",
                        options=pair.options if hasattr(pair, 'options') else None,
                        option_explanations=None,
                        question_type=pair.question_type.upper(),
                        knowledge_type="CONCEPT",
                        covered_node_ids=[chapter_node_id],
                        difficulty=3,
                        tags=[chapter_title],
                        question_metadata={
                            "created_by": created_by,
                            "created_at": datetime.now().isoformat(),
                            "importance": 0.7,
                            "hits": 0,
                            "misses": 0,
                            "review_interval_days": 1.0,
                            "auto_generated": True,
                        },
                        source_material_ids=source_mats,
                    ))
            except Exception as e:
                logger.warning("Failed to generate %s questions for chapter %s: %s", q_type, chapter_node_id, e)

        if all_new_questions:
            async with AsyncSessionLocal() as db:
                for q in all_new_questions:
                    db.add(q)
                await db.commit()
                logger.info(
                    "Auto-generated %d questions for chapter node %s (%s)",
                    len(all_new_questions), chapter_node_id, chapter_title,
                )
    except Exception as e:
        logger.error("Failed to auto-generate questions for chapter %s: %s", chapter_node_id, e)


async def _get_or_create_material(
    db: AsyncSession,
    project_id: str,
    video_url: str,
    title: str,
    channel: Optional[str],
    created_by: str = "",
    material_id: Optional[str] = None,
) -> MaterialModel:
    if material_id:
        result = await db.execute(
            select(MaterialModel).where(
                MaterialModel.project_id == project_id,
                MaterialModel.id == material_id,
            )
        )
        existing_by_id = result.scalar_one_or_none()
        if existing_by_id:
            if video_url and not existing_by_id.source_url:
                existing_by_id.source_url = video_url
            if title and existing_by_id.title != title:
                existing_by_id.title = title
            existing_by_id.updated_at = datetime.now()
            return existing_by_id

    result = await db.execute(
        select(MaterialModel).where(
            MaterialModel.project_id == project_id,
            MaterialModel.source_url == video_url,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if title and existing.title != title:
            existing.title = title
            existing.updated_at = datetime.now()
        return existing

    new_material_id = material_id or f"material-{int(datetime.now().timestamp() * 1000)}"
    material = MaterialModel(
        id=new_material_id,
        project_id=project_id,
        created_by=created_by,
        title=title,
        source_url=video_url,
        content_text="",
        transcript_text=None,
        transcript_segments=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(material)
    await db.flush()
    return material


async def _get_or_create_chapter_node(
    db: AsyncSession,
    project_id: str,
    material_id: str,
    title: str,
    video_url: str,
    created_by: str = "",
) -> tuple[str, int]:
    """Create or return a chapter node for a video, and wire a VIDEO_SEQUENCE edge from the previous chapter."""
    index_key = (project_id, video_url)

    # --- cache hit ---
    existing = _chapter_index_by_source.get(index_key)
    if existing:
        result = await db.execute(
            select(NodeModel.id).where(
                NodeModel.project_id == project_id,
                NodeModel.id == existing,
            )
        )
        if result.scalar_one_or_none():
            chapters_result = await db.execute(
                select(NodeModel.id)
                .where(NodeModel.project_id == project_id, NodeModel.id.like("chapter_%"))
                .order_by(NodeModel.created_at)
            )
            chapter_ids = [r[0] for r in chapters_result.fetchall()]
            seq = (chapter_ids.index(existing) + 1) if existing in chapter_ids else 1
            return existing, seq

    # --- load all existing chapter nodes from DB (used for sequence + restart recovery) ---
    chapters_result = await db.execute(
        select(NodeModel)
        .where(NodeModel.project_id == project_id, NodeModel.id.like("chapter_%"))
        .order_by(NodeModel.created_at)
    )
    existing_chapters = chapters_result.scalars().all()

    # --- DB-level dedup: check if a chapter for this material already exists (handles restarts) ---
    for ch in existing_chapters:
        if material_id in (ch.source_material_ids or []):
            chapter_ids = [c.id for c in existing_chapters]
            seq = (chapter_ids.index(ch.id) + 1) if ch.id in chapter_ids else 1
            _chapter_index_by_source[index_key] = ch.id  # repopulate cache
            return ch.id, seq

    sequence_number = len(existing_chapters) + 1
    prev_chapter = existing_chapters[-1] if existing_chapters else None

    chapter_id = f"chapter_{int(datetime.now().timestamp() * 1000)}"
    chapter_node = NodeModel(
        id=chapter_id,
        project_id=project_id,
        created_by=created_by,
        topic_name=title,
        proven_knowledge_rating=0.0,
        user_estimated_knowledge_rating=0.0,
        importance=0.9,
        relevance=1.0,
        view_frequency=1,
        source_material_ids=[material_id],
    )
    db.add(chapter_node)
    await db.flush()

    # Link to previous chapter with a VIDEO_SEQUENCE edge
    if prev_chapter is not None:
        seq_edge_id = f"{prev_chapter.id}-{chapter_id}-VIDEO_SEQUENCE"
        if not await _edge_exists(db, project_id, prev_chapter.id, chapter_id, EdgeType.VIDEO_SEQUENCE):
            seq_edge = EdgeModel(
                id=seq_edge_id,
                project_id=project_id,
                source=prev_chapter.id,
                target=chapter_id,
                type=EdgeType.VIDEO_SEQUENCE.value,
                weight=1.0,
            )
            db.add(seq_edge)

    _chapter_index_by_source[index_key] = chapter_id
    return chapter_id, sequence_number


async def _get_or_create_topic_node(
    db: AsyncSession,
    project_id: str,
    topic_name: str,
    material_id: str,
    created_by: str = "",
) -> str:
    topic_key = _normalize_topic_key(topic_name)
    if not topic_key:
        raise ValueError("Topic name cannot be empty")

    index_key = (project_id, topic_key)
    node_id = _topic_id_from_key(topic_key, project_id)
    legacy_node_id = _topic_id_from_key(topic_key)  # old-style without project hash

    # --- cache hit ---
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

    # --- DB-level dedup: check new-style project-scoped ID first ---
    result = await db.execute(
        select(NodeModel).where(
            NodeModel.project_id == project_id,
            NodeModel.id == node_id,
        )
    )
    existing_node = result.scalar_one_or_none()
    if existing_node:
        source_ids = set(existing_node.source_material_ids or [])
        source_ids.add(material_id)
        existing_node.source_material_ids = list(source_ids)
        _topic_index_by_key[index_key] = node_id  # repopulate cache
        return node_id

    # --- backward compat: check legacy ID for this project ---
    if legacy_node_id != node_id:
        result = await db.execute(
            select(NodeModel).where(
                NodeModel.project_id == project_id,
                NodeModel.id == legacy_node_id,
            )
        )
        existing_node = result.scalar_one_or_none()
        if existing_node:
            source_ids = set(existing_node.source_material_ids or [])
            source_ids.add(material_id)
            existing_node.source_material_ids = list(source_ids)
            _topic_index_by_key[index_key] = legacy_node_id  # repopulate cache
            return legacy_node_id

    # --- not found anywhere: insert with project-scoped ID ---
    node = NodeModel(
        id=node_id,
        project_id=project_id,
        created_by=created_by,
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
async def create_node(
    request: CreateNodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
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

    background_tasks.add_task(
        _auto_generate_questions_for_node,
        project_id=request.project_id,
        node_id=node.id,
        topic_name=request.topic_name,
        created_by=created_by,
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
        logger.warning("Node update failed: not found node_id=%s project_id=%s", node_id, request.project_id)
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
async def ingest_video(request: VideoIngestRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Ingest a video transcript, extract topics, and merge into the graph."""
    if not request.video_url.strip():
        raise HTTPException(status_code=400, detail="video_url is required")
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    default_user = await _get_default_user(db)
    created_by = default_user.username if default_user else ""

    transcript = request.transcript
    if not transcript:
        transcript, _ = await asyncio.to_thread(fetch_youtube_transcript, request.video_url)

    topics = request.topics
    if not topics:
        topics = await asyncio.to_thread(extract_topics_from_text, transcript, request.title)
    topics = [topic.strip() for topic in topics if topic.strip()]
    logger.info("Video ingest: project_id=%s title=%s topics=%s", request.project_id, request.title, len(topics))

    if not topics:
        raise HTTPException(status_code=400, detail="No topics extracted")

    material = await _get_or_create_material(
        db,
        request.project_id,
        request.video_url,
        request.title,
        request.channel,
        created_by=created_by,
        material_id=request.material_id,
    )

    chapter_created = False
    chapter_node_id: str | None = None
    sequence_number: int | None = None
    if request.include_chapter_node:
        chapter_created = (request.project_id, request.video_url) not in _chapter_index_by_source
        chapter_node_id, sequence_number = await _get_or_create_chapter_node(
            db,
            request.project_id,
            material.id,
            request.title,
            request.video_url,
            created_by=created_by,
        )

    topics_result = []
    edges_added = 0
    pending_edge_ids: set[str] = set()  # track edges added in this batch to avoid duplicates

    # Generate questions for the chapter node (video-level comprehension)
    if chapter_created and chapter_node_id:
        background_tasks.add_task(
            _auto_generate_questions_for_chapter,
            project_id=request.project_id,
            chapter_node_id=chapter_node_id,
            chapter_title=request.title,
            created_by=created_by,
            transcript_text=transcript or "",
            material_id=material.id,
        )

    for topic in topics:
        topic_key = _normalize_topic_key(topic)
        index_key = (request.project_id, topic_key)
        existing_topic_id = _topic_index_by_key.get(index_key)
        topic_node_id = await _get_or_create_topic_node(
            db,
            request.project_id,
            topic,
            material.id,
            created_by=created_by,
        )

        if chapter_node_id:
            edge_id = f"{chapter_node_id}-{topic_node_id}-{EdgeType.SUBCONCEPT_OF.value}"
            if edge_id not in pending_edge_ids and not await _edge_exists(
                db,
                request.project_id,
                chapter_node_id,
                topic_node_id,
                EdgeType.SUBCONCEPT_OF,
            ):
                edge = EdgeModel(
                    id=edge_id,
                    project_id=request.project_id,
                    source=chapter_node_id,
                    target=topic_node_id,
                    type=EdgeType.SUBCONCEPT_OF.value,
                    weight=0.9,
                )
                db.add(edge)
                pending_edge_ids.add(edge_id)
                edges_added += 1

            chapter_neighbors = _topic_chapter_index.get((request.project_id, topic_node_id), set())
            for other_chapter_id in sorted(chapter_neighbors):
                if other_chapter_id == chapter_node_id:
                    continue
                edge_id = f"{other_chapter_id}-{chapter_node_id}-{EdgeType.APPLIED_WITH.value}"
                if edge_id in pending_edge_ids:
                    continue
                if not await _edge_exists(
                    db,
                    request.project_id,
                    other_chapter_id,
                    chapter_node_id,
                    EdgeType.APPLIED_WITH,
                ):
                    edge = EdgeModel(
                        id=edge_id,
                        project_id=request.project_id,
                        source=other_chapter_id,
                        target=chapter_node_id,
                        type=EdgeType.APPLIED_WITH.value,
                        weight=0.4,
                    )
                    db.add(edge)
                    pending_edge_ids.add(edge_id)
                    edges_added += 1

            _topic_chapter_index.setdefault((request.project_id, topic_node_id), set()).add(chapter_node_id)

        if existing_topic_id is None:
            background_tasks.add_task(
                _auto_generate_questions_for_node,
                project_id=request.project_id,
                node_id=topic_node_id,
                topic_name=topic,
                created_by=created_by,
                transcript_context=transcript or "",
                material_id=material.id,
            )

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
        "sequence_number": sequence_number,
        "topics": topics_result,
        "edges_added": edges_added,
        "graph": await _serialize_graph_summary(request.project_id, db),
    }
