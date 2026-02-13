"""Material/content management API endpoints."""

import asyncio
from datetime import datetime
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Material as MaterialModel,
    AppUser as AppUserModel,
    Node as NodeModel,
    Question as QuestionModel,
)
from app.services.node_suggestions.embedding_service import EmbeddingService
from app.services.node_suggestions.keyword_extraction_service import KeywordExtractionService
from app.services.node_suggestions.node_suggestion_service import NodeSuggestionService
from app.services.node_suggestions.postgres_repository import PostgresNodeSuggestionRepository
from app.services.video_transcripts import (
    extract_youtube_video_id,
    fetch_youtube_transcript_segments,
    looks_like_single_url,
    transcript_to_text,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_content_sessions = {}
_session_counter = 0


def _material_chunks(content_text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in content_text.split("\n\n") if chunk.strip()]
    if chunks:
        return chunks
    return [chunk.strip() for chunk in content_text.split("\n") if chunk.strip()]


def _optional_chunks(content_text: str | None) -> list[str]:
    if not content_text:
        return []
    return _material_chunks(content_text)


def _normalize_transcript_segments(segments: list[dict] | list[object] | None) -> list[dict]:
    normalized: list[dict] = []
    for segment in segments or []:
        if isinstance(segment, dict):
            raw_text = segment.get("text")
            raw_start = segment.get("start")
            raw_duration = segment.get("duration")
        else:
            raw_text = getattr(segment, "text", None)
            raw_start = getattr(segment, "start", None)
            raw_duration = getattr(segment, "duration", None)

        text_value = (raw_text or "").strip()
        if not text_value:
            continue

        item = {"text": text_value}
        if raw_start is not None:
            item["start"] = float(raw_start)
        if raw_duration is not None:
            item["duration"] = float(raw_duration)
        normalized.append(item)
    return normalized


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


def _serialize_material(material: MaterialModel) -> dict:
    transcript_chunks = _optional_chunks(getattr(material, "transcript_text", None))
    transcript_segments = getattr(material, "transcript_segments", None) or []
    return {
        "id": material.id,
        "project_id": material.project_id,
        "created_by": material.created_by,
        "title": material.title,
        "source_url": material.source_url,
        "chunk_count": len(_material_chunks(material.content_text)),
        "transcript_chunk_count": len(transcript_chunks),
        "transcript_segment_count": len(transcript_segments),
        "has_transcript": bool(transcript_chunks),
    }


def _normalize_title(value: str) -> str:
    return " ".join(value.lower().strip().split())


async def _fetch_youtube_transcript(link: str) -> tuple[str, str, list[dict]]:
    video_id = extract_youtube_video_id(link)
    if not video_id:
        logger.warning("YouTube transcript fetch failed: invalid_link=%s", link)
        raise HTTPException(status_code=400, detail="Invalid YouTube link")

    try:
        segments, strategy_used = await asyncio.to_thread(fetch_youtube_transcript_segments, link)
        normalized_segments = _normalize_transcript_segments(segments)
        content_text = transcript_to_text(normalized_segments)
    except Exception as exc:
        raw_detail = str(exc)
        log_detail = raw_detail
        if "ParseError" in raw_detail:
            log_detail = (
                "youtube_transcript_api ParseError; this often means the installed library is outdated "
                "or YouTube response format changed. "
                f"{raw_detail}"
            )
        logger.exception(
            "YouTube transcript fetch failed in service: video_id=%s link=%s error=%s",
            video_id,
            link,
            log_detail,
        )
        raise HTTPException(status_code=400, detail="Unable to fetch transcript.") from exc

    if not content_text.strip():
        logger.warning(
            "YouTube transcript fetch returned empty transcript: video_id=%s link=%s",
            video_id,
            link,
        )
        raise HTTPException(status_code=400, detail="YouTube transcript is empty")

    logger.info(
        "YouTube transcript fetched successfully: video_id=%s segments=%s chars=%s",
        video_id,
        len(_material_chunks(content_text)),
        len(content_text),
    )
    return content_text, strategy_used, normalized_segments


@router.post("/materials/youtube/transcript-check")
async def check_youtube_transcript(data: dict):
    """Check whether a YouTube video has transcript and return parsed text when available."""
    link = (data or {}).get("link") or (data or {}).get("source_url")
    if not link:
        raise HTTPException(status_code=400, detail="link is required")

    content_text, strategy_used, segments = await _fetch_youtube_transcript(link)
    video_id = extract_youtube_video_id(link)
    chunks = _material_chunks(content_text)
    return {
        "link": link,
        "video_id": video_id,
        "has_transcript": True,
        "fetch_strategy": strategy_used,
        "transcript_text": content_text,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "segments": segments,
    }


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


@router.get("/materials")
async def list_materials(
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """List available materials for a project."""
    result = await db.execute(
        select(MaterialModel).where(MaterialModel.project_id == project_id)
    )
    materials = result.scalars().all()
    return [_serialize_material(material) for material in materials]


@router.get("/materials/{material_id}")
async def get_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """Get material content by ID."""
    result = await db.execute(
        select(MaterialModel).where(MaterialModel.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return {
        "id": material.id,
        "title": material.title,
        "source_url": material.source_url,
        "chunks": _material_chunks(material.content_text),
        "transcript_text": material.transcript_text or "",
        "transcript_chunks": _optional_chunks(material.transcript_text),
        "transcript_segments": material.transcript_segments or [],
    }


@router.post("/materials")
async def create_material(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new material."""
    project_id = data.get("project_id")
    title = data.get("title")
    source_url = (data.get("source_url") or data.get("link") or "").strip()
    content_text = (data.get("content_text") or "").strip()
    transcript_text = (data.get("transcript_text") or "").strip()
    transcript_segments = _normalize_transcript_segments(data.get("transcript_segments") or [])
    if not project_id or not title:
        raise HTTPException(status_code=400, detail="project_id and title are required")

    imported_from_youtube = False
    imported_video_id = None

    if not source_url and looks_like_single_url(content_text):
        detected_video_id = extract_youtube_video_id(content_text)
        if detected_video_id:
            source_url = content_text
            content_text = ""
            logger.info(
                "Material create detected YouTube URL in content_text: project_id=%s title=%s video_id=%s",
                project_id,
                title,
                detected_video_id,
            )

    logger.info(
        "Material create request: project_id=%s title=%s has_source_url=%s has_content_text=%s",
        project_id,
        title,
        bool(source_url),
        bool(content_text),
    )

    if source_url and transcript_text:
        imported_from_youtube = True
        imported_video_id = extract_youtube_video_id(source_url)

    if not content_text and source_url and not transcript_text:
        transcript_text, fetch_strategy, transcript_segments = await _fetch_youtube_transcript(source_url)
        content_text = transcript_text
        imported_from_youtube = True
        imported_video_id = extract_youtube_video_id(source_url)
        logger.info(
            "Material create YouTube import strategy: material_title=%s strategy=%s",
            title,
            fetch_strategy,
        )

    if not content_text and not transcript_text:
        raise HTTPException(status_code=400, detail="content_text is required unless a valid YouTube link is provided")

    material_id = data.get("id") or f"material-{int(datetime.now().timestamp())}"
    result = await db.execute(select(MaterialModel).where(MaterialModel.id == material_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Material already exists")

    default_user = await _get_default_user(db)
    created_by = data.get("created_by") or (default_user.username if default_user else "")

    material = MaterialModel(
        id=material_id,
        project_id=project_id,
        created_by=created_by,
        title=title,
        source_url=source_url,
        content_text=content_text,
        transcript_text=transcript_text or None,
        transcript_segments=transcript_segments or None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    payload = _serialize_material(material)
    payload.update(
        {
            "imported_from_youtube": imported_from_youtube,
            "youtube_video_id": imported_video_id,
            "transcript_chunk_count": len(_optional_chunks(transcript_text)) if imported_from_youtube else 0,
        }
    )
    logger.info(
        "Material create success: material_id=%s imported_from_youtube=%s video_id=%s",
        material.id,
        imported_from_youtube,
        imported_video_id,
    )
    return payload


@router.patch("/materials/{material_id}")
async def update_material(material_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a material title or content."""
    result = await db.execute(
        select(MaterialModel).where(MaterialModel.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    incoming_source_url = None
    if "source_url" in data or "link" in data:
        incoming_source_url = (data.get("source_url") or data.get("link") or "").strip()

    if "title" in data:
        material.title = data["title"]
    if incoming_source_url is not None:
        material.source_url = incoming_source_url or None
    if "content_text" in data:
        material.content_text = data.get("content_text") or ""

    if incoming_source_url is not None and not incoming_source_url:
        material.transcript_text = None
        material.transcript_segments = None
    elif "transcript_text" in data:
        transcript_text = (data.get("transcript_text") or "").strip()
        material.transcript_text = transcript_text or None

    if "transcript_segments" in data:
        transcript_segments = _normalize_transcript_segments(data.get("transcript_segments") or [])
        material.transcript_segments = transcript_segments or None

    material.updated_at = datetime.now()

    await db.commit()
    await db.refresh(material)
    return _serialize_material(material)


@router.delete("/materials/{material_id}")
async def delete_material(material_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a material."""
    result = await db.execute(
        select(MaterialModel).where(MaterialModel.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    await db.delete(material)
    await db.commit()
    return {"status": "deleted"}


@router.post("/materials/{material_id}/attach")
async def attach_material(
    material_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Attach a material to nodes and/or questions."""
    result = await db.execute(
        select(MaterialModel).where(MaterialModel.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    node_ids = data.get("node_ids") or []
    question_ids = data.get("question_ids") or []

    if not node_ids and not question_ids:
        raise HTTPException(
            status_code=400,
            detail="node_ids or question_ids are required",
        )

    attached_nodes = 0
    attached_questions = 0

    if node_ids:
        nodes_result = await db.execute(
            select(NodeModel).where(
                NodeModel.project_id == material.project_id,
                NodeModel.id.in_(node_ids),
            )
        )
        nodes = nodes_result.scalars().all()
        found_node_ids = {node.id for node in nodes}
        missing_nodes = sorted(set(node_ids) - found_node_ids)
        if missing_nodes:
            raise HTTPException(
                status_code=404,
                detail=f"Nodes not found: {', '.join(missing_nodes)}",
            )

        for node in nodes:
            source_ids = set(node.source_material_ids or [])
            if material_id not in source_ids:
                source_ids.add(material_id)
                node.source_material_ids = list(source_ids)
                attached_nodes += 1

    if question_ids:
        questions_result = await db.execute(
            select(QuestionModel).where(
                QuestionModel.project_id == material.project_id,
                QuestionModel.id.in_(question_ids),
            )
        )
        questions = questions_result.scalars().all()
        found_question_ids = {question.id for question in questions}
        missing_questions = sorted(set(question_ids) - found_question_ids)
        if missing_questions:
            raise HTTPException(
                status_code=404,
                detail=f"Questions not found: {', '.join(missing_questions)}",
            )

        for question in questions:
            source_ids = set(question.source_material_ids or [])
            if material_id not in source_ids:
                source_ids.add(material_id)
                question.source_material_ids = list(source_ids)
                attached_questions += 1

    await db.commit()

    return {
        "material_id": material_id,
        "attached_nodes": attached_nodes,
        "attached_questions": attached_questions,
    }


@router.put("/materials/{material_id}/nodes")
async def replace_material_nodes(
    material_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Replace the set of nodes linked to a material."""
    logger.info(
        "Replace material nodes request: material_id=%s payload_keys=%s",
        material_id,
        list((data or {}).keys()),
    )
    result = await db.execute(
        select(MaterialModel).where(MaterialModel.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        logger.warning("Material not found: material_id=%s", material_id)
        raise HTTPException(status_code=404, detail="Material not found")

    node_ids = data.get("node_ids") or []
    new_nodes = data.get("new_nodes") or []

    filtered_node_ids = [node_id for node_id in node_ids if not node_id.startswith("material:")]
    ignored_ids = sorted(set(node_ids) - set(filtered_node_ids))
    if ignored_ids:
        logger.warning(
            "Replace material nodes ignoring material node_ids: material_id=%s ignored=%s",
            material_id,
            ignored_ids,
        )
    node_ids = filtered_node_ids

    if not node_ids and not new_nodes:
        logger.info(
            "Replace material nodes clearing all links: material_id=%s",
            material_id,
        )

    logger.info(
        "Replace material nodes payload: material_id=%s node_ids=%s new_nodes=%s",
        material_id,
        len(node_ids),
        len(new_nodes),
    )

    nodes_result = await db.execute(
        select(NodeModel).where(NodeModel.project_id == material.project_id)
    )
    nodes = nodes_result.scalars().all()
    node_map = {node.id: node for node in nodes}
    title_map = {
        _normalize_title(node.topic_name): node.id
        for node in nodes
        if node.topic_name
    }

    desired_ids = {node_id for node_id in node_ids if node_id in node_map}
    missing_ids = sorted(set(node_ids) - set(node_map))
    if missing_ids:
        logger.warning(
            "Replace material nodes missing node_ids: material_id=%s missing=%s",
            material_id,
            missing_ids,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Nodes not found: {', '.join(missing_ids)}",
        )

    created_nodes: list[NodeModel] = []
    created_node_ids: list[str] = []
    if new_nodes:
        default_user = await _get_default_user(db)
        created_by = default_user.username if default_user else ""
        for entry in new_nodes:
            title = None
            if isinstance(entry, str):
                title = entry
            elif isinstance(entry, dict):
                title = entry.get("title") or entry.get("suggested_title")
            if not title or not title.strip():
                logger.warning(
                    "Replace material nodes invalid new_nodes title: material_id=%s entry=%s",
                    material_id,
                    entry,
                )
                raise HTTPException(status_code=400, detail="new_nodes titles are required")

            normalized = _normalize_title(title)
            existing_id = title_map.get(normalized)
            if existing_id:
                logger.info(
                    "Replace material nodes reused existing node: material_id=%s title=%s node_id=%s",
                    material_id,
                    title,
                    existing_id,
                )
                desired_ids.add(existing_id)
                continue

            node_id = f"node_{uuid.uuid4().hex}"
            node = NodeModel(
                id=node_id,
                project_id=material.project_id,
                created_by=created_by,
                topic_name=title.strip(),
                proven_knowledge_rating=0.0,
                user_estimated_knowledge_rating=0.0,
                importance=0.5,
                relevance=0.5,
                view_frequency=0,
                source_material_ids=[material_id],
            )
            db.add(node)
            created_nodes.append(node)
            created_node_ids.append(node_id)
            desired_ids.add(node_id)
            title_map[normalized] = node_id
            logger.info(
                "Replace material nodes created node: material_id=%s node_id=%s title=%s",
                material_id,
                node_id,
                title,
            )

        if created_nodes:
            await db.flush()
            for node in created_nodes:
                await _update_node_search_vector(db, node.id)
            nodes.extend(created_nodes)

    for node in nodes:
        source_ids = set(node.source_material_ids or [])
        if node.id in desired_ids:
            source_ids.add(material_id)
        else:
            source_ids.discard(material_id)
        node.source_material_ids = list(source_ids)

    await db.commit()

    logger.info(
        "Replace material nodes complete: material_id=%s node_ids=%s created=%s",
        material_id,
        len(desired_ids),
        len(created_node_ids),
    )
    return {
        "material_id": material_id,
        "node_ids": sorted(desired_ids),
        "created_node_ids": created_node_ids,
    }


@router.post("/materials/{material_id}/suggestions")
async def suggest_nodes_for_material(
    material_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Suggest nodes for a material by wrapping the raw-text suggestion workflow."""
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    result = await db.execute(
        select(MaterialModel).where(MaterialModel.id == material_id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    combined_parts = [
        (material.content_text or "").strip(),
        (material.transcript_text or "").strip(),
    ]
    combined_text = "\n\n".join([part for part in combined_parts if part])

    return await suggest_nodes_for_material_text(
        data={
            "project_id": project_id,
            "text": combined_text,
            "threshold": float(data.get("threshold", settings.SUGGESTION_THRESHOLD)),
            "semantic_weight": float(data.get("semantic_weight", settings.SUGGESTION_SEMANTIC_WEIGHT)),
            "keyword_weight": float(data.get("keyword_weight", settings.SUGGESTION_KEYWORD_WEIGHT)),
            "top_k": int(data.get("top_k", settings.SUGGESTION_TOP_K)),
            "dedup_threshold": float(data.get("dedup_threshold", settings.SUGGESTION_DEDUP_THRESHOLD)),
            "material_id": material_id,
        },
        db=db,
    )


@router.post("/materials/suggestions/raw-text")
async def suggest_nodes_for_material_text(data: dict, db: AsyncSession = Depends(get_db)):
    """Suggest nodes from raw text using the shared hybrid workflow."""
    threshold = float(data.get("threshold", settings.SUGGESTION_THRESHOLD))
    semantic_weight = float(data.get("semantic_weight", settings.SUGGESTION_SEMANTIC_WEIGHT))
    keyword_weight = float(data.get("keyword_weight", settings.SUGGESTION_KEYWORD_WEIGHT))
    top_k = int(data.get("top_k", settings.SUGGESTION_TOP_K))
    dedup_threshold = float(data.get("dedup_threshold", settings.SUGGESTION_DEDUP_THRESHOLD))
    project_id = data.get("project_id")
    text_value = (data.get("text") or "").strip()
    material_id = data.get("material_id")

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    if not text_value:
        return {"strong": [], "weak": []}

    hf_token = settings.HF_TOKEN or os.environ.get("HF_TOKEN")
    if not hf_token:
        raise HTTPException(status_code=400, detail="HF_TOKEN is required")

    from huggingface_hub import InferenceClient

    hf_base_url = os.environ.get(
        "HF_INFERENCE_BASE_URL",
        "https://router.huggingface.co/hf-inference",
    )
    client = InferenceClient(token=hf_token, base_url=hf_base_url)
    embedding_service = EmbeddingService(client, expected_dim=768)
    keyword_service = KeywordExtractionService(client)
    repository = PostgresNodeSuggestionRepository(db)
    service = NodeSuggestionService(repository, embedding_service, keyword_service)
    try:
        result = await service.suggest_nodes_for_text(
            project_id=project_id,
            text=text_value,
            threshold=threshold,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            top_k=top_k,
            dedup_threshold=dedup_threshold,
            material_id=material_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Node suggestion failed: {exc}") from exc

    return {
        "strong": [item.__dict__ for item in result.strong],
        "weak": [item.__dict__ for item in result.weak],
    }


@router.post("/materials/sessions")
async def start_content_session(data: dict, db: AsyncSession = Depends(get_db)):
    """Start a new content reading session."""
    global _session_counter
    _session_counter += 1

    payload = data or {}
    material_id = payload.get("material_id")
    if not material_id:
        result = await db.execute(select(MaterialModel.id).limit(1))
        material_id = result.scalar_one_or_none()
    if not material_id:
        raise HTTPException(status_code=400, detail="No materials available")

    user_id = payload.get("user_id")
    if not user_id:
        default_user = await _get_default_user(db)
        user_id = default_user.id if default_user else ""

    session_id = f"content-{_session_counter}"
    now = datetime.now()

    _content_sessions[session_id] = {
        "session_id": session_id,
        "material_id": material_id,
        "user_id": user_id,
        "started_at": now.isoformat(),
        "last_interjection_at": None,
        "consumed_chunks": 0,
    }

    return _content_sessions[session_id]


@router.post("/materials/sessions/{session_id}/report-chunk")
async def report_chunk_consumed(session_id: str, data: dict):
    """Report that chunks have been consumed."""
    if session_id not in _content_sessions:
        return {"error": "Session not found"}, 404

    consumed_chunks = data.get("consumed_chunks", 0)
    _content_sessions[session_id]["consumed_chunks"] = consumed_chunks

    return _content_sessions[session_id]


@router.get("/materials/sessions/{session_id}/should-interject")
async def should_interject(session_id: str):
    """Check if an interjection question should be asked."""
    if session_id not in _content_sessions:
        return {"error": "Session not found"}, 404

    session = _content_sessions[session_id]
    consumed = session.get("consumed_chunks", 0)

    should = consumed > 0 and consumed % 2 == 0

    return {
        "should_interject": should,
        "reason": "Review checkpoint" if should else None,
    }


@router.get("/materials/sessions/{session_id}/interjection-question")
async def get_interjection_question(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get an interjection question for a content session."""
    if session_id not in _content_sessions:
        return {"error": "Session not found"}, 404
    session = _content_sessions[session_id]
    material_id = session.get("material_id")
    title = "this material"
    if material_id:
        result = await db.execute(
            select(MaterialModel).where(MaterialModel.id == material_id)
        )
        material = result.scalar_one_or_none()
        if material:
            title = material.title

    return {
        "id": f"{session_id}-interjection",
        "text": f"Summarize the main idea from {title}.",
        "answer": "",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": [],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 1,
        "tags": ["interjection"],
        "last_attempted_at": None,
        "source_material_ids": [],
    }


@router.post("/materials/sessions/{session_id}/submit-interjection")
async def submit_interjection_answer(session_id: str, data: dict):
    """Submit an answer to an interjection question."""
    if session_id not in _content_sessions:
        return {"error": "Session not found"}, 404

    return {
        "correct": True,
        "correct_answer": None,
        "explanation": "Thanks for your response.",
    }
