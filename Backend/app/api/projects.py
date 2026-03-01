"""Project management API endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Project as ProjectModel, AppUser as AppUserModel

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_project(project: ProjectModel) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
        "created_by": project.created_by,
        "visibility": project.visibility,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all available projects."""
    result = await db.execute(select(ProjectModel))
    projects = result.scalars().all()
    return [_serialize_project(project) for project in projects]


@router.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific project by ID."""
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _serialize_project(project)


@router.post("/projects")
async def create_project(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new project."""
    project_id = data.get("id") or f"project-{int(datetime.now().timestamp())}"
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Project already exists")

    now = datetime.now()
    owner_id = data.get("owner_id")
    if not owner_id:
        default_user = await _get_default_user(db)
        if not default_user:
            raise HTTPException(status_code=400, detail="No default user found")
        owner_id = default_user.id
    default_user = await _get_default_user(db)
    created_by = data.get("created_by") or (default_user.username if default_user else owner_id)

    project = ProjectModel(
        id=project_id,
        name=data.get("name", "Untitled Project"),
        description=data.get("description", ""),
        owner_id=owner_id,
        created_by=created_by,
        visibility=data.get("visibility", "private"),
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    logger.info("Project created: project_id=%s name=%s", project.id, project.name)
    return _serialize_project(project)


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an existing project."""
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field in ("name", "description", "visibility", "owner_id"):
        if field in data:
            setattr(project, field, data[field])
    project.updated_at = datetime.now()

    await db.commit()
    await db.refresh(project)
    return _serialize_project(project)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project."""
    result = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    logger.info("Project deleted: project_id=%s", project_id)
    return {"status": "deleted"}
