"""Community management API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Community as CommunityModel, AppUser as AppUserModel, Node as NodeModel

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_community(community: CommunityModel) -> dict:
    return {
        "id": community.id,
        "name": community.name,
        "description": community.description,
        "created_by": community.created_by,
        "project_ids": community.project_ids or [],
        "member_ids": community.member_ids or [],
        "node_importance_overrides": community.node_importance_overrides or {},
        "question_importance_overrides": community.question_importance_overrides or {},
    }


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


@router.get("/communities")
async def list_communities(db: AsyncSession = Depends(get_db)):
    """List all available communities."""
    result = await db.execute(select(CommunityModel))
    communities = result.scalars().all()
    return [_serialize_community(community) for community in communities]


@router.get("/communities/{community_id}")
async def get_community(community_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific community."""
    result = await db.execute(
        select(CommunityModel).where(CommunityModel.id == community_id)
    )
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return _serialize_community(community)


@router.post("/communities")
async def create_community(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new community."""
    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    community_id = data.get("id") or f"community-{int(datetime.now().timestamp())}"
    result = await db.execute(select(CommunityModel).where(CommunityModel.id == community_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Community already exists")

    default_user = await _get_default_user(db)
    created_by = data.get("created_by") or (default_user.username if default_user else "")

    community = CommunityModel(
        id=community_id,
        name=name,
        description=data.get("description", ""),
        created_by=created_by,
        project_ids=data.get("project_ids", []),
        member_ids=data.get("member_ids", []),
        node_importance_overrides=data.get("node_importance_overrides", {}),
        question_importance_overrides=data.get("question_importance_overrides", {}),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(community)
    await db.commit()
    await db.refresh(community)
    return _serialize_community(community)


@router.patch("/communities/{community_id}")
async def update_community(community_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an existing community."""
    result = await db.execute(select(CommunityModel).where(CommunityModel.id == community_id))
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    for field in (
        "name",
        "description",
        "project_ids",
        "member_ids",
        "node_importance_overrides",
        "question_importance_overrides",
    ):
        if field in data:
            setattr(community, field, data[field])
    community.updated_at = datetime.now()

    await db.commit()
    await db.refresh(community)
    return _serialize_community(community)


@router.delete("/communities/{community_id}")
async def delete_community(community_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a community."""
    result = await db.execute(select(CommunityModel).where(CommunityModel.id == community_id))
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    await db.delete(community)
    await db.commit()
    return {"status": "deleted"}


@router.post("/communities/active")
async def set_active_community(data: dict, db: AsyncSession = Depends(get_db)):
    """Set the active community for the current user."""
    community_id = data.get("community_id")
    if not community_id:
        raise HTTPException(status_code=400, detail="community_id is required")

    result = await db.execute(
        select(CommunityModel).where(CommunityModel.id == community_id)
    )
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    user_id = data.get("user_id")
    if user_id:
        user_result = await db.execute(
            select(AppUserModel).where(AppUserModel.id == user_id)
        )
        user = user_result.scalar_one_or_none()
    else:
        user = await _get_default_user(db)

    if not user:
        raise HTTPException(status_code=400, detail="No user available")

    user.active_community_id = community_id
    await db.commit()
    return {"community_id": community_id}


@router.get("/communities/{community_id}/progress")
async def get_community_progress(community_id: str, db: AsyncSession = Depends(get_db)):
    """Get progress metrics for a community."""
    result = await db.execute(
        select(CommunityModel).where(CommunityModel.id == community_id)
    )
    community = result.scalar_one_or_none()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    project_ids = community.project_ids or []
    override_count = sum(
        len(nodes) for nodes in (community.node_importance_overrides or {}).values()
    )

    total_nodes = 0
    avg_knowledge = 0.0
    if project_ids:
        result = await db.execute(
            select(
                func.count(NodeModel.id),
                func.coalesce(func.avg(NodeModel.proven_knowledge_rating), 0.0),
            ).where(NodeModel.project_id.in_(project_ids))
        )
        row = result.one()
        total_nodes = row[0] or 0
        avg_knowledge = float(row[1])

    return {
        "community_id": community_id,
        "overall_progress": avg_knowledge,
        "relevant_topics": total_nodes,
    }


@router.get("/communities/{community_id}/leaderboard")
async def get_community_leaderboard(community_id: str, db: AsyncSession = Depends(get_db)):
    """Get leaderboard for a community."""
    result = await db.execute(
        select(CommunityModel.id).where(CommunityModel.id == community_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Community not found")

    return []
