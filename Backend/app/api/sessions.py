"""Session management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import AppUser as AppUserModel

router = APIRouter()

# In-memory storage for demo
_sessions = {}
_session_counter = 0


async def _get_default_user_id(db: AsyncSession) -> str:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="No default user found")
    return user.id


@router.post("/sessions")
async def start_session(data: dict = None, db: AsyncSession = Depends(get_db)):
    """Start a new content session."""
    global _session_counter
    _session_counter += 1
    
    session_id = f"session-{_session_counter}"
    now = datetime.now()
    
    payload = data or {}
    user_id = payload.get("user_id") or await _get_default_user_id(db)
    material_id = payload.get("material_id", "material-1")

    _sessions[session_id] = {
        "session_id": session_id,
        "material_id": material_id,
        "user_id": user_id,
        "started_at": now.isoformat(),
        "last_interjection_at": None,
        "consumed_chunks": 0,
    }
    
    return _sessions[session_id]


@router.get("/sessions/current")
async def get_current_session(db: AsyncSession = Depends(get_db)):
    """Get the current active session, if any."""
    # Return the most recent session if available
    if _sessions:
        return list(_sessions.values())[-1]

    # No session found, create a default one
    return await start_session({}, db)
