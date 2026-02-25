"""API routes package.

Combines all API routers into a single main router.
This router is then included in the FastAPI app with the /api/v1 prefix.
"""
from fastapi import APIRouter
from app.api import auth, graph, communities, revision, sessions, materials, projects, questions, users, search, qa_generation

# Create main API router
api_router = APIRouter()

# Authentication routes
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Graph routes
api_router.include_router(
    graph.router,
    tags=["Graph"]
)

# Community routes
api_router.include_router(
    communities.router,
    tags=["Communities"]
)

# Revision session routes
api_router.include_router(
    revision.router,
    tags=["Revision"]
)

# Content session routes
api_router.include_router(
    sessions.router,
    tags=["Sessions"]
)

# Materials routes
api_router.include_router(
    materials.router,
    tags=["Materials"]
)

# Project routes
api_router.include_router(
    projects.router,
    tags=["Projects"]
)

# Question routes
api_router.include_router(
    questions.router,
    tags=["Questions"]
)

# QA generation routes
api_router.include_router(
    qa_generation.router,
    tags=["Questions"]
)

# User routes
api_router.include_router(
    users.router,
    tags=["Users"]
)

# Search routes
api_router.include_router(
    search.router,
    tags=["Search"]
)
