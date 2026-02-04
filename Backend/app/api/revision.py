"""Revision session and question answering API endpoints."""

from fastapi import APIRouter
from datetime import datetime
from app.api.llm_verification import verify_answer_with_llm

router = APIRouter()

# In-memory storage for demo
_sessions = {}
_session_counter = 0

# All available questions with MCQ options
_all_questions = [
    {
        "id": "q1",
        "text": "What is a variable in Python?",
        "answer": "A variable is a named container that stores a value",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["variables"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 1,
        "tags": ["fundamentals"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q2",
        "text": "What are the basic data types in Python?",
        "answer": "int, float, str, bool, list, dict, tuple, set",
        "question_type": "MCQ",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["variables"],
        "options": [
            "int, float, str, bool, list, dict, tuple, set",
            "int, float, string, boolean, array, object",
            "integer, decimal, text, logical, collection, map",
            "number, decimal, character, logic, array, hash"
        ],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 2,
        "tags": ["fundamentals"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q3",
        "text": "What is the purpose of a function?",
        "answer": "Functions encapsulate reusable code blocks",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["functions"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 2,
        "tags": ["fundamentals"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q4",
        "text": "How do you define a function in Python?",
        "answer": "Using the def keyword",
        "question_type": "MCQ",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["functions"],
        "options": [
            "Using the def keyword",
            "Using the function keyword",
            "Using the fn keyword",
            "Using the func keyword"
        ],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 1,
        "tags": ["fundamentals"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q5",
        "text": "What is a class in Python?",
        "answer": "A blueprint for creating objects",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["classes"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 3,
        "tags": ["oop"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q6",
        "text": "What is inheritance in OOP?",
        "answer": "A mechanism to inherit properties and methods from parent classes",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["inheritance"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 3,
        "tags": ["oop"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q7",
        "text": "What is polymorphism?",
        "answer": "The ability to have multiple forms or behaviors",
        "question_type": "MCQ",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["inheritance"],
        "options": [
            "The ability to have multiple forms or behaviors",
            "The process of inheritance",
            "The ability to hide implementation details",
            "The reuse of code through inheritance"
        ],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 4,
        "tags": ["oop"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q8",
        "text": "What are decorators used for?",
        "answer": "Decorators modify the behavior of functions or classes",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["decorators"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 4,
        "tags": ["advanced"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q9",
        "text": "What is async programming?",
        "answer": "Asynchronous programming allows concurrent execution",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["async"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 5,
        "tags": ["advanced"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
    {
        "id": "q10",
        "text": "What is OOP?",
        "answer": "Object-Oriented Programming is a paradigm based on objects and classes",
        "question_type": "OPEN",
        "knowledge_type": "CONCEPT",
        "covered_node_ids": ["oop"],
        "metadata": {
            "created_by": "system",
            "created_at": datetime.now().isoformat(),
            "importance": 1,
            "hits": 0,
            "misses": 0,
        },
        "difficulty": 2,
        "tags": ["oop"],
        "last_attempted_at": None,
        "source_material_ids": [],
    },
]


@router.post("/revision/sessions")
async def start_revision_session():
    """Start a new revision session."""
    global _session_counter
    _session_counter += 1
    
    session_id = f"session-{_session_counter}"
    _sessions[session_id] = {
        "session_id": session_id,
        "max_questions": 10,
        "started_at": datetime.now().isoformat(),
        "questions_answered": 0,
        "question_index": 0,
    }
    
    return {
        "session_id": session_id,
        "max_questions": 10,
    }


@router.get("/revision/sessions/{session_id}/next-question")
async def get_next_question(session_id: str):
    """Get the next question for a revision session."""
    if session_id not in _sessions:
        return {"error": "Session not found"}, 404
    
    session = _sessions[session_id]
    question_index = session.get("question_index", 0)
    
    # Cycle through questions
    if question_index >= len(_all_questions):
        question_index = 0
    
    question = dict(_all_questions[question_index])
    session["question_index"] = question_index + 1
    session["current_question_id"] = question["id"]
    
    # Don't return the answer to the frontend
    question_response = {k: v for k, v in question.items() if k != "answer"}
    
    return question_response


@router.post("/revision/sessions/{session_id}/submit-answer")
async def submit_revision_answer(session_id: str, data: dict):
    """Submit an answer to a question in a revision session."""
    if session_id not in _sessions:
        return {"error": "Session not found"}, 404
    
    session = _sessions[session_id]
    question_id = data.get("question_id")
    user_answer = data.get("answer", "").strip()
    
    # Increment question counter
    session["questions_answered"] = session.get("questions_answered", 0) + 1
    
    if not user_answer:
        return {
            "correct": False,
            "correct_answer": "Please provide an answer.",
        }
    
    # Find the question
    question = None
    for q in _all_questions:
        if q["id"] == question_id:
            question = q
            break
    
    if not question:
        return {
            "correct": False,
            "correct_answer": "Question not found.",
        }
    
    # For MCQ questions, check if the answer matches exactly
    if question["question_type"] == "MCQ":
        is_correct = user_answer.lower() == question["answer"].lower()
        return {
            "correct": is_correct,
            "correct_answer": question["answer"],
            "explanation": "Correct!" if is_correct else f"Not quite. The correct answer is: {question['answer']}",
        }
    
    # For OPEN questions, use LLM verification
    verification_result = await verify_answer_with_llm(
        user_answer=user_answer,
        correct_answer=question["answer"],
        question_text=question["text"],
    )
    
    return {
        "correct": verification_result["correct"],
        "correct_answer": question["answer"],
        "explanation": verification_result["explanation"],
    }
