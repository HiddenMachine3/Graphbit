"""Material/content management API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Material as MaterialModel, AppUser as AppUserModel

router = APIRouter()

_content_sessions = {}
_session_counter = 0


def _material_chunks(content_text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in content_text.split("\n\n") if chunk.strip()]
    if chunks:
        return chunks
    return [chunk.strip() for chunk in content_text.split("\n") if chunk.strip()]


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


def _serialize_material(material: MaterialModel) -> dict:
    return {
        "id": material.id,
        "project_id": material.project_id,
        "created_by": material.created_by,
        "title": material.title,
        "chunk_count": len(_material_chunks(material.content_text)),
    }


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
        "chunks": _material_chunks(material.content_text),
    }


@router.post("/materials")
async def create_material(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new material."""
    project_id = data.get("project_id")
    title = data.get("title")
    content_text = data.get("content_text")
    if not project_id or not title or not content_text:
        raise HTTPException(status_code=400, detail="project_id, title, and content_text are required")

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
        content_text=content_text,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(material)
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
