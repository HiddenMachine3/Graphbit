"""Revision session and question answering API endpoints.

Implements the GraphRecall algorithm for intelligent question selection:
- 5-factor weighted scoring (knowledge gaps, importance, staleness, difficulty, failures)
- Topic-diversity round-robin grouping
- Stateful sessions with locked question IDs
"""
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.llm_verification import verify_answer_with_llm
from app.db.session import get_db
from app.models import Question as QuestionModel, RevisionSession as RevisionSessionModel, Node as NodeModel

router = APIRouter()
logger = logging.getLogger(__name__)

PERFORMANCE_LEVELS = {"bad", "ok", "good", "great"}

# ── GraphRecall Scoring Weights ──────────────────────────────────────────────
W_KNOWLEDGE = 0.35   # Prioritize topics user knows least
W_IMPORTANCE = 0.20  # Prioritize high-importance nodes
W_STALENESS = 0.20   # Prioritize questions not seen recently
W_DIFFICULTY = 0.10  # Slightly favor harder questions
W_FAILURES = 0.15    # Resurface frequently-failed questions


def _score_question_graphrecall(
    question: QuestionModel,
    nodes_map: dict[str, NodeModel],
    now: datetime,
) -> float:
    """Score a question using the GraphRecall algorithm.
    
    Returns a float where HIGHER = higher priority to show.
    """
    covered_nodes = question.covered_node_ids or []
    q_meta = question.question_metadata or {}

    # ── Factor 1: Knowledge Gap (1 - avg PKR) ────────────────────────────
    avg_pkr = 0.0
    avg_importance = 0.5
    valid_nodes = 0
    for node_id in covered_nodes:
        node = nodes_map.get(node_id)
        if node:
            avg_pkr += getattr(node, "proven_knowledge_rating", 0.0) or 0.0
            avg_importance += getattr(node, "importance", 0.5) or 0.5
            valid_nodes += 1
    if valid_nodes > 0:
        avg_pkr /= valid_nodes
        avg_importance /= valid_nodes

    knowledge_gap = 1.0 - avg_pkr  # Higher when user knows less

    # ── Factor 2: Importance ──────────────────────────────────────────────
    importance_score = avg_importance

    # ── Factor 3: Staleness ───────────────────────────────────────────────
    staleness = 1.0  # Never seen = maximum staleness
    if question.last_attempted_at:
        try:
            last_seen = question.last_attempted_at
            if isinstance(last_seen, str):
                last_seen = datetime.fromisoformat(last_seen)
            days_since = max(0, (now - last_seen).total_seconds() / 86400)
            staleness = min(1.0, days_since / 14.0)
        except (ValueError, TypeError):
            staleness = 1.0

    # ── Factor 4: Difficulty ──────────────────────────────────────────────
    difficulty = getattr(question, "difficulty", 3) or 3
    difficulty_norm = min(1.0, difficulty / 5.0)

    # ── Factor 5: Failure Ratio ───────────────────────────────────────────
    hits = int(q_meta.get("hits", 0))
    misses = int(q_meta.get("misses", 0))
    total_attempts = hits + misses
    failure_ratio = misses / max(1, total_attempts) if total_attempts > 0 else 0.5

    # ── Weighted Sum ──────────────────────────────────────────────────────
    score = (
        W_KNOWLEDGE * knowledge_gap
        + W_IMPORTANCE * importance_score
        + W_STALENESS * staleness
        + W_DIFFICULTY * difficulty_norm
        + W_FAILURES * failure_ratio
    )

    return score


def _select_questions_with_diversity(
    questions: list[QuestionModel],
    nodes_map: dict[str, NodeModel],
    max_count: int,
    now: datetime,
) -> list[str]:
    """Select and diversify questions using round-robin topic grouping.
    
    Returns a list of question IDs, interleaved by topic.
    """
    if not questions:
        return []

    # Score every question
    scored = []
    for q in questions:
        score = _score_question_graphrecall(q, nodes_map, now)
        primary_node = (q.covered_node_ids or ["__uncategorized__"])[0]
        scored.append((q, score, primary_node))

    # Sort by score descending (higher priority first)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Group by primary node (topic)
    topic_groups: dict[str, list] = defaultdict(list)
    for q, score, primary_node in scored:
        topic_groups[primary_node].append(q)

    # Round-robin interleave across topics
    result_ids: list[str] = []
    seen_ids: set[str] = set()

    # Sort topics by their best question score (highest first)
    sorted_topics = sorted(
        topic_groups.keys(),
        key=lambda t: max(
            _score_question_graphrecall(q, nodes_map, now)
            for q in topic_groups[t]
        ),
        reverse=True,
    )

    # Round-robin pick: take 1 from each topic in order, repeat
    topic_indices = {t: 0 for t in sorted_topics}
    while len(result_ids) < max_count:
        added_any = False
        for topic in sorted_topics:
            if len(result_ids) >= max_count:
                break
            idx = topic_indices[topic]
            group = topic_groups[topic]
            if idx < len(group):
                q = group[idx]
                if q.id not in seen_ids:
                    result_ids.append(q.id)
                    seen_ids.add(q.id)
                    added_any = True
                topic_indices[topic] = idx + 1
        if not added_any:
            break  # All topics exhausted

    return result_ids


# ── API Endpoints ────────────────────────────────────────────────────────────


@router.post("/revision/sessions")
async def start_revision_session(data: dict, db: AsyncSession = Depends(get_db)):
    """Start a new revision session with locked-in questions."""
    project_id = data.get("project_id") if data else None
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    max_questions = data.get("max_questions", 10)
    try:
        max_questions = int(max_questions)
    except (ValueError, TypeError):
        max_questions = 10

    # ── Fetch all questions for the project ───────────────────────────────
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    all_questions = list(result.scalars().all())

    # ── Fetch all nodes for scoring ───────────────────────────────────────
    nodes_result = await db.execute(
        select(NodeModel).where(NodeModel.project_id == project_id)
    )
    nodes_map = {node.id: node for node in nodes_result.scalars().all()}

    # ── Run GraphRecall algorithm ─────────────────────────────────────────
    now = datetime.now()
    selected_ids = _select_questions_with_diversity(
        all_questions, nodes_map, max_questions, now
    )

    # Clamp max_questions to what's actually available
    actual_max = len(selected_ids)

    session_id = f"session-{uuid.uuid4().hex[:12]}"
    session = RevisionSessionModel(
        id=session_id,
        project_id=project_id,
        max_questions=actual_max,
        question_ids=selected_ids,
        started_at=now,
    )
    db.add(session)
    await db.commit()

    logger.info(
        "Revision session started: session_id=%s project_id=%s questions=%d/%d",
        session_id, project_id, actual_max, len(all_questions),
    )
    return {
        "session_id": session_id,
        "max_questions": actual_max,
        "project_id": project_id,
    }


@router.get("/revision/sessions/{session_id}/next-question")
async def get_next_question(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get the next question from the locked session list."""
    result = await db.execute(
        select(RevisionSessionModel).where(RevisionSessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question_ids = session.question_ids or []

    # ── Session complete check ────────────────────────────────────────────
    if session.question_index >= len(question_ids) or session.questions_answered >= session.max_questions:
        return {"session_complete": True, "questions_answered": session.questions_answered}

    # ── Fetch the exact next question ─────────────────────────────────────
    next_question_id = question_ids[session.question_index]
    q_result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == next_question_id)
    )
    db_question = q_result.scalar_one_or_none()

    if not db_question:
        # Skip missing question, advance index
        await db.execute(
            update(RevisionSessionModel)
            .where(RevisionSessionModel.id == session_id)
            .values(question_index=session.question_index + 1)
        )
        await db.commit()
        # Recurse to get next valid question
        return await get_next_question(session_id, db)

    # ── Update session tracking ───────────────────────────────────────────
    await db.execute(
        update(RevisionSessionModel)
        .where(RevisionSessionModel.id == session_id)
        .values(
            question_index=session.question_index + 1,
            current_question_id=db_question.id,
        )
    )
    await db.commit()

    # ── Return question (without answer for non-flashcards) ───────────────
    payload = {
        "id": db_question.id,
        "text": db_question.text,
        "options": db_question.options,
        "question_type": db_question.question_type,
        "knowledge_type": db_question.knowledge_type,
        "covered_node_ids": db_question.covered_node_ids,
        "difficulty": db_question.difficulty,
        "tags": db_question.tags,
    }
    if db_question.question_type == "FLASHCARD":
        payload["answer"] = db_question.answer
    return payload


@router.post("/revision/sessions/{session_id}/submit-answer")
async def submit_revision_answer(session_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Submit an answer to a question in a revision session."""
    result = await db.execute(
        select(RevisionSessionModel).where(RevisionSessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question_id = data.get("question_id")
    user_answer = data.get("answer", "").strip()
    performance = (data.get("performance") or "").strip().lower()

    # ── Increment answered counter ────────────────────────────────────────
    await db.execute(
        update(RevisionSessionModel)
        .where(RevisionSessionModel.id == session_id)
        .values(questions_answered=session.questions_answered + 1)
    )

    if not user_answer and performance not in PERFORMANCE_LEVELS:
        await db.commit()
        return {
            "correct": False,
            "correct_answer": "Please provide an answer or flashcard performance rating.",
        }

    # ── Find question ─────────────────────────────────────────────────────
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()

    if not question:
        await db.commit()
        return {
            "correct": False,
            "correct_answer": "Question not found.",
        }

    response = {}
    is_correct_for_stats = False

    # ── Evaluate answer by type ───────────────────────────────────────────
    if question.question_type == "FLASHCARD":
        if performance not in PERFORMANCE_LEVELS:
            await db.commit()
            return {
                "correct": False,
                "correct_answer": "Performance rating is required for flashcards (bad/ok/good/great).",
            }
        is_correct_for_stats = performance in {"good", "great"}
        response = {
            "correct": True,
            "correct_answer": question.answer,
            "performance": performance,
            "explanation": "Flashcard performance recorded.",
        }

    elif question.question_type == "MCQ":
        is_correct = user_answer.lower() == question.answer.lower()
        is_correct_for_stats = is_correct
        explanation = None
        if question.option_explanations and user_answer in question.option_explanations:
            explanation = question.option_explanations[user_answer]
        else:
            explanation = (
                "Correct. This is the right answer."
                if is_correct
                else f"Incorrect. The correct answer is: {question.answer}"
            )
        response = {
            "correct": is_correct,
            "correct_answer": question.answer,
            "explanation": explanation,
        }

    else:
        # OPEN questions — LLM verification
        logger.info("Verifying open answer: session_id=%s question_id=%s", session_id, question_id)
        verification_result = await verify_answer_with_llm(
            user_answer=user_answer,
            correct_answer=question.answer,
            question_text=question.text,
        )
        is_correct_for_stats = verification_result["correct"]
        response = {
            "correct": verification_result["correct"],
            "correct_answer": question.answer,
            "explanation": verification_result["explanation"],
        }
        if verification_result.get("score") is not None:
            response["score"] = verification_result["score"]

    # ── Update Question Metadata (spaced repetition) ──────────────────────
    metadata = question.question_metadata or {}
    if not isinstance(metadata, dict):
        metadata = {}

    if question.question_type == "FLASHCARD":
        ratings = (
            metadata.get("flashcard_ratings")
            if isinstance(metadata.get("flashcard_ratings"), dict)
            else {level: 0 for level in PERFORMANCE_LEVELS}
        )
        ratings[performance] = int(ratings.get(performance, 0)) + 1
        metadata["flashcard_ratings"] = ratings
        metadata["last_flashcard_rating"] = performance

    hits = int(metadata.get("hits", 0))
    misses = int(metadata.get("misses", 0))
    current_interval = float(metadata.get("review_interval_days", 1.0))

    if is_correct_for_stats:
        hits += 1
        new_interval = current_interval * 2.0
    else:
        misses += 1
        new_interval = 0.01  # ~14 minutes

    metadata["hits"] = hits
    metadata["misses"] = misses
    metadata["review_interval_days"] = new_interval
    metadata["next_review_at"] = (datetime.now() + timedelta(days=new_interval)).isoformat()

    question.question_metadata = metadata
    question.last_attempted_at = datetime.now()

    # ── Update Node Mastery (PKR recalculation) ───────────────────────────
    if question.covered_node_ids:
        for node_id in question.covered_node_ids:
            try:
                node_res = await db.execute(select(NodeModel).where(NodeModel.id == node_id))
                node = node_res.scalar_one_or_none()
                if not node:
                    continue

                q_res = await db.execute(
                    select(QuestionModel).where(QuestionModel.project_id == node.project_id)
                )
                all_qs = q_res.scalars().all()

                rates = []
                for q in all_qs:
                    c_ids = q.covered_node_ids or []
                    if node.id in c_ids:
                        q_meta = q.question_metadata or {}
                        h = int(q_meta.get("hits", 0))
                        m = int(q_meta.get("misses", 0))
                        if h + m > 0:
                            rates.append(h / (h + m))

                node.proven_knowledge_rating = sum(rates) / len(rates) if rates else 0.0
            except Exception as e:
                logger.error(f"Error recalculating node mastery: {e}")

    await db.commit()
    return response
