"""Question management API endpoints."""

from datetime import datetime
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models import Question as QuestionModel, AppUser as AppUserModel, Node as NodeModel
from app.services.node_suggestions.confidence import compute_confidence
from app.services.node_suggestions.deduplication import deduplicate_candidates
from app.services.node_suggestions.embedding_service import EmbeddingService
from app.services.node_suggestions.keyword_extraction_service import KeywordExtractionService
from app.services.node_suggestions.postgres_repository import PostgresNodeSuggestionRepository
from app.services.node_suggestions.ranking_service import RankingService
from app.services.node_suggestions.types import CandidatePhrase, SuggestionItem, SuggestionRequest
from app.services.node_suggestions.utils import chunk_text, cosine_similarity

router = APIRouter()
logger = logging.getLogger(__name__)


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


def _normalize_title(value: str) -> str:
    return " ".join(value.lower().strip().split())


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


def _question_text(question: QuestionModel) -> str:
    parts = [question.text or "", question.answer or ""]
    return "\n\n".join([part for part in parts if part.strip()])


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


@router.put("/questions/{question_id}/nodes")
async def replace_question_nodes(
    question_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Replace the set of nodes linked to a question."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    node_ids = data.get("node_ids") or []
    new_nodes = data.get("new_nodes") or []
    filtered_node_ids = [node_id for node_id in node_ids if not node_id.startswith("material:")]
    node_ids = filtered_node_ids

    nodes_result = await db.execute(
        select(NodeModel).where(NodeModel.project_id == question.project_id)
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
                raise HTTPException(status_code=400, detail="new_nodes titles are required")

            normalized = _normalize_title(title)
            existing_id = title_map.get(normalized)
            if existing_id:
                desired_ids.add(existing_id)
                continue

            node_id = f"node_{uuid.uuid4().hex}"
            node = NodeModel(
                id=node_id,
                project_id=question.project_id,
                created_by=created_by,
                topic_name=title.strip(),
                proven_knowledge_rating=0.0,
                user_estimated_knowledge_rating=0.0,
                importance=0.0,
                relevance=0.5,
                view_frequency=0,
                source_material_ids=[],
            )
            db.add(node)
            created_nodes.append(node)
            created_node_ids.append(node_id)
            desired_ids.add(node_id)
            title_map[normalized] = node_id

        if created_nodes:
            await db.flush()
            for node in created_nodes:
                await _update_node_search_vector(db, node.id)

    question.covered_node_ids = sorted(desired_ids)
    await db.commit()

    return {
        "question_id": question_id,
        "node_ids": sorted(desired_ids),
        "created_node_ids": created_node_ids,
    }


@router.post("/questions/{question_id}/suggestions")
async def suggest_nodes_for_question(
    question_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Suggest nodes for a question using hybrid search."""
    threshold = float(data.get("threshold", settings.SUGGESTION_THRESHOLD))
    semantic_weight = float(data.get("semantic_weight", settings.SUGGESTION_SEMANTIC_WEIGHT))
    keyword_weight = float(data.get("keyword_weight", settings.SUGGESTION_KEYWORD_WEIGHT))
    top_k = int(data.get("top_k", settings.SUGGESTION_TOP_K))
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    hf_token = settings.HF_TOKEN or os.environ.get("HF_TOKEN")
    if not hf_token:
        raise HTTPException(status_code=400, detail="HF_TOKEN is required")

    from huggingface_hub import InferenceClient

    client = InferenceClient(provider="hf-inference", api_key=hf_token)
    embedding_service = EmbeddingService(client, expected_dim=768)
    keyword_service = KeywordExtractionService(client)
    repository = PostgresNodeSuggestionRepository(db)

    question_text = _question_text(question)
    if not question_text.strip():
        return {"strong": [], "weak": []}

    material_embedding = embedding_service.embed_texts([question_text])[0]

    vector_matches = await repository.search_nodes_vector(
        project_id,
        material_embedding,
        top_k,
    )
    keyword_matches = await repository.search_nodes_fts(
        project_id,
        question_text,
        top_k,
    )

    semantic_scores = {match.node_id: match.score for match in vector_matches}
    keyword_scores = {match.node_id: match.score for match in keyword_matches}

    ranked = RankingService.hybrid_rank(
        semantic_scores,
        keyword_scores,
        semantic_weight,
        keyword_weight,
    )

    strong: list[SuggestionItem] = []
    weak: list[SuggestionItem] = []
    for match in ranked:
        item = SuggestionItem(
            node_id=match.node_id,
            suggested_title=None,
            suggested_description=None,
            confidence=match.score,
            suggestion_type="EXISTING",
        )
        if match.score >= threshold:
            strong.append(item)
        else:
            weak.append(item)

    candidate_phrases = keyword_service.extract_phrases(question_text)
    chunks = chunk_text(question_text)
    total_chunks = max(len(chunks), 1)

    candidate_embeddings = []
    if candidate_phrases:
        candidate_embeddings = embedding_service.embed_texts(candidate_phrases)

    candidates: list[CandidatePhrase] = [
        CandidatePhrase(phrase=phrase, embedding=embedding)
        for phrase, embedding in zip(candidate_phrases, candidate_embeddings)
    ]

    similarity_lookup = {}
    for candidate in candidates:
        similarity_lookup[candidate.phrase] = await repository.max_similarity_to_nodes(
            project_id,
            candidate.embedding,
        )

    candidates = deduplicate_candidates(
        candidates,
        similarity_lookup,
        threshold=settings.SUGGESTION_DEDUP_THRESHOLD,
    )

    for candidate in candidates:
        coverage = sum(
            1 for chunk in chunks if candidate.phrase.lower() in chunk.lower()
        ) / total_chunks
        semantic_strength = cosine_similarity(candidate.embedding, material_embedding)
        confidence = compute_confidence(coverage, semantic_strength)
        weak.append(
            SuggestionItem(
                node_id=None,
                suggested_title=candidate.phrase,
                suggested_description=None,
                confidence=confidence,
                suggestion_type="NEW",
            )
        )

    logger.info(
        "Running node suggestions for question %s (project %s)",
        question_id,
        project_id,
    )

    return {
        "strong": [item.__dict__ for item in strong],
        "weak": [item.__dict__ for item in weak],
    }


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
