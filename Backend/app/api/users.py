"""User management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import AppUser as AppUserModel

router = APIRouter()


def _serialize_user(user: AppUserModel) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "active_community_id": user.active_community_id,
    }


@router.get("/users/me")
async def get_current_user(db: AsyncSession = Depends(get_db)):
    """Return the default logged-in user."""
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(user)
