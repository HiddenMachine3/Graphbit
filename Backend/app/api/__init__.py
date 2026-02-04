"""API routes package.

Combines all API routers into a single main router.
This router is then included in the FastAPI app with the /api/v1 prefix.
"""
from fastapi import APIRouter
from app.api import auth

# Create main API router
api_router = APIRouter()

# Authentication routes
# POST /auth/register - Register new user
# POST /auth/login - Login and get JWT token (accepts form data)
# GET /auth/me - Get current user info (protected)
# POST /auth/logout - Logout (optional, mostly client-side)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)
