"""Material/content management API endpoints."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

# In-memory storage for demo materials
_materials = {
    "material-1": {
        "id": "material-1",
        "title": "Binary Search – Conceptual Understanding",
        "chunks": [
            "Binary search is a divide-and-conquer algorithm.",
            "It works on sorted arrays by repeatedly halving the search space.",
            "The time complexity of binary search is O(log n).",
            "Binary search relies on the invariant that the array is sorted.",
            "Incorrect mid calculation can cause overflow in some languages.",
        ],
    },
    "material-2": {
        "id": "material-2",
        "title": "Python Functions",
        "chunks": [
            "A function is a reusable block of code.",
            "Functions improve code organization and readability.",
            "Parameters allow functions to accept inputs.",
            "Return statements allow functions to produce outputs.",
            "Scope determines variable visibility within functions.",
        ],
    },
}

_content_sessions = {}
_session_counter = 0


@router.get("/materials")
async def list_materials():
    """List available materials."""
    return [
        {
            "id": material["id"],
            "title": material["title"],
            "chunk_count": len(material["chunks"]),
        }
        for material in _materials.values()
    ]


@router.get("/materials/{material_id}")
async def get_material(material_id: str):
    """Get material content by ID."""
    if material_id not in _materials:
        return {"error": "Material not found"}, 404
    
    return _materials[material_id]


@router.post("/materials/sessions")
async def start_content_session(data: dict):
    """Start a new content reading session."""
    global _session_counter
    _session_counter += 1
    
    material_id = data.get("material_id", "material-1")
    user_id = data.get("user_id", "user-1")
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
    
    # Ask a question every 2 chunks
    should = consumed > 0 and consumed % 2 == 0
    
    return {
        "should_interject": should,
        "reason": "This is a good time to test your understanding." if should else None,
    }


@router.get("/materials/sessions/{session_id}/interjection-question")
async def get_interjection_question(session_id: str):
    """Get an interjection question for a content session."""
    if session_id not in _content_sessions:
        return {"error": "Session not found"}, 404
    
    return {
        "id": "q-interject-1",
        "text": "What is the time complexity of binary search?",
        "answer": "O(log n)",
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
        "tags": ["important"],
        "last_attempted_at": None,
        "source_material_ids": ["material-1"],
    }


@router.post("/materials/sessions/{session_id}/submit-interjection")
async def submit_interjection_answer(session_id: str, data: dict):
    """Submit an answer to an interjection question."""
    if session_id not in _content_sessions:
        return {"error": "Session not found"}, 404
    
    return {
        "correct": True,
        "correct_answer": "O(log n)",
        "explanation": "Correct! Binary search cuts the search space in half each iteration.",
    }
