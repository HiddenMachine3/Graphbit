"""Question management API endpoints."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Question as QuestionModel, AppUser as AppUserModel

router = APIRouter()


def _serialize_question(question: QuestionModel) -> dict:
    return {
        "id": question.id,
        "project_id": question.project_id,
        "created_by": question.created_by,
        "text": question.text,
        "answer": question.answer,
        "options": question.options,
        "option_explanations": question.option_explanations,
        "question_type": question.question_type,
        "knowledge_type": question.knowledge_type,
        "covered_node_ids": question.covered_node_ids,
        "difficulty": question.difficulty,
        "tags": question.tags,
        "question_metadata": question.question_metadata,
        "last_attempted_at": question.last_attempted_at.isoformat()
        if question.last_attempted_at
        else None,
        "source_material_ids": question.source_material_ids,
    }


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


@router.get("/questions")
async def list_questions(
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """List questions for a project."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    questions = result.scalars().all()
    return [_serialize_question(question) for question in questions]


@router.get("/questions/{question_id}")
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific question by ID."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return _serialize_question(question)


@router.post("/questions")
async def create_question(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new question."""
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    text = data.get("text")
    answer = data.get("answer")
    if not text or not answer:
        raise HTTPException(status_code=400, detail="text and answer are required")

    question_id = data.get("id") or f"question-{int(datetime.now().timestamp())}"
    existing = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Question already exists")

    default_user = await _get_default_user(db)
    created_by = data.get("created_by") or (default_user.username if default_user else "")

    question = QuestionModel(
        id=question_id,
        project_id=project_id,
        created_by=created_by,
        text=text,
        answer=answer,
        options=data.get("options"),
        option_explanations=data.get("option_explanations"),
        question_type=data.get("question_type", "OPEN"),
        knowledge_type=data.get("knowledge_type", "CONCEPT"),
        covered_node_ids=data.get("covered_node_ids", []),
        difficulty=data.get("difficulty", 1),
        tags=data.get("tags", []),
        question_metadata={
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
            "importance": data.get("importance", 0.2),
            "hits": 0,
            "misses": 0,
        },
        last_attempted_at=None,
        source_material_ids=data.get("source_material_ids", []),
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return _serialize_question(question)


@router.patch("/questions/{question_id}")
async def update_question(question_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an existing question."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    for field in (
        "text",
        "answer",
        "options",
        "option_explanations",
        "question_type",
        "knowledge_type",
        "covered_node_ids",
        "difficulty",
        "tags",
        "source_material_ids",
    ):
        if field in data:
            setattr(question, field, data[field])

    if "question_metadata" in data and isinstance(data["question_metadata"], dict):
        question.question_metadata = data["question_metadata"]

    await db.commit()
    await db.refresh(question)
    return _serialize_question(question)


@router.delete("/questions/{question_id}")
async def delete_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a question."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()
    return {"status": "deleted"}
