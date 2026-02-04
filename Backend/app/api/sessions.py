"""Session management API endpoints."""

from fastapi import APIRouter
from datetime import datetime
from typing import Optional

router = APIRouter()

# In-memory storage for demo
_sessions = {}
_session_counter = 0


@router.post("/sessions")
async def start_session(data: dict = None):
    """Start a new content session."""
    global _session_counter
    _session_counter += 1
    
    session_id = f"session-{_session_counter}"
    now = datetime.now()
    
    _sessions[session_id] = {
        "session_id": session_id,
        "material_id": "material-1",
        "user_id": "user-1",
        "started_at": now.isoformat(),
        "last_interjection_at": None,
        "consumed_chunks": 0,
    }
    
    return _sessions[session_id]


@router.get("/sessions/current")
async def get_current_session():
    """Get the current active session, if any."""
    # Return the most recent session if available
    if _sessions:
        return list(_sessions.values())[-1]
    
    # No session found
    return None
