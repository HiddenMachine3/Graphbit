"""Revision session and question answering API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from app.api.llm_verification import verify_answer_with_llm
from app.db.session import get_db
from app.models import Question as QuestionModel, RevisionSession as RevisionSessionModel
import uuid

router = APIRouter()


@router.post("/revision/sessions")
async def start_revision_session(data: dict, db: AsyncSession = Depends(get_db)):
    """Start a new revision session."""
    project_id = data.get("project_id") if data else None
    if not project_id:
        return {"error": "project_id is required"}, 400
    session_id = f"session-{uuid.uuid4().hex[:12]}"
    
    session = RevisionSessionModel(
        id=session_id,
        project_id=project_id,
        max_questions=10,
        started_at=datetime.now(),
    )
    
    db.add(session)
    await db.commit()
    
    return {
        "session_id": session_id,
        "max_questions": 10,
        "project_id": project_id,
    }


@router.get("/revision/sessions/{session_id}/next-question")
async def get_next_question(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get the next question for a revision session."""
    # Fetch session from database
    result = await db.execute(
        select(RevisionSessionModel).where(RevisionSessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return {"error": "Session not found"}, 404
    
    # Fetch questions for project
    query = select(QuestionModel)
    if session.project_id:
        query = query.where(QuestionModel.project_id == session.project_id)
    result = await db.execute(query)
    all_questions = result.scalars().all()
    
    if not all_questions:
        return {"error": "No questions available"}, 404
    
    # Cycle through questions
    question_index = session.question_index
    if question_index >= len(all_questions):
        question_index = 0
    
    db_question = all_questions[question_index]
    
    # Update session
    await db.execute(
        update(RevisionSessionModel)
        .where(RevisionSessionModel.id == session_id)
        .values(
            question_index=question_index + 1,
            current_question_id=db_question.id
        )
    )
    await db.commit()
    
    # Return question without the answer
    return {
        "id": db_question.id,
        "text": db_question.text,
        "options": db_question.options,
        "question_type": db_question.question_type,
        "knowledge_type": db_question.knowledge_type,
        "covered_node_ids": db_question.covered_node_ids,
        "difficulty": db_question.difficulty,
        "tags": db_question.tags,
    }


@router.post("/revision/sessions/{session_id}/submit-answer")
async def submit_revision_answer(session_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Submit an answer to a question in a revision session."""
    # Fetch session from database
    result = await db.execute(
        select(RevisionSessionModel).where(RevisionSessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return {"error": "Session not found"}, 404
    
    question_id = data.get("question_id")
    user_answer = data.get("answer", "").strip()
    
    # Increment question counter
    await db.execute(
        update(RevisionSessionModel)
        .where(RevisionSessionModel.id == session_id)
        .values(questions_answered=session.questions_answered + 1)
    )
    
    if not user_answer:
        await db.commit()
        return {
            "correct": False,
            "correct_answer": "Please provide an answer.",
        }
    
    # Find the question in database
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
    
    # For MCQ questions, check if the answer matches exactly
    if question.question_type == "MCQ":
        is_correct = user_answer.lower() == question.answer.lower()
        explanation = None
        if question.option_explanations and user_answer in question.option_explanations:
            explanation = question.option_explanations[user_answer]
        else:
            if is_correct:
                explanation = "Correct. This is the right answer."
            else:
                explanation = f"Incorrect. The correct answer is: {question.answer}"
        await db.commit()
        return {
            "correct": is_correct,
            "correct_answer": question.answer,
            "explanation": explanation,
        }
    
    # For OPEN questions, use LLM verification
    verification_result = await verify_answer_with_llm(
        user_answer=user_answer,
        correct_answer=question.answer,
        question_text=question.text,
    )
    
    response = {
        "correct": verification_result["correct"],
        "correct_answer": question.answer,
        "explanation": verification_result["explanation"],
    }
    
    # Include score if available (from Hugging Face reward model)
    if verification_result.get("score") is not None:
        response["score"] = verification_result["score"]
    
    await db.commit()
    return response
