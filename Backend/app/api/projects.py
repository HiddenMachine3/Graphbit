"""Project management API endpoints."""

from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

# In-memory storage for demo projects (replace with database queries)
_now = datetime.now().isoformat()
_projects = {
    "demo_project": {
        "id": "demo_project",
        "name": "Demo Project",
        "description": "Default demo project for development",
        "owner_id": "demo_user",
        "visibility": "private",
        "created_at": _now,
        "updated_at": _now,
    }
}


@router.get("/projects")
async def list_projects():
    """List all available projects."""
    return list(_projects.values())


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project by ID."""
    if project_id not in _projects:
        return {"error": "Project not found"}, 404
    return _projects[project_id]


@router.post("/projects")
async def create_project(data: dict):
    """Create a new project (demo-only in-memory)."""
    project_id = data.get("id") or f"project-{len(_projects) + 1}"
    now = datetime.now().isoformat()
    project = {
        "id": project_id,
        "name": data.get("name", "Untitled Project"),
        "description": data.get("description", ""),
        "owner_id": data.get("owner_id", "demo_user"),
        "visibility": data.get("visibility", "private"),
        "created_at": now,
        "updated_at": now,
    }
    _projects[project_id] = project
    return project


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, data: dict):
    """Update an existing project (demo-only in-memory)."""
    if project_id not in _projects:
        return {"error": "Project not found"}, 404

    project = _projects[project_id]
    for field in ("name", "description", "visibility"):
        if field in data:
            project[field] = data[field]

    project["updated_at"] = datetime.now().isoformat()
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project (demo-only in-memory)."""
    if project_id not in _projects:
        return {"error": "Project not found"}, 404

    del _projects[project_id]
    return {"status": "deleted"}
