"""Main FastAPI application entry point.

This file:
- Creates the FastAPI app instance
- Configures CORS for frontend communication
- Sets up database initialization on startup
- Includes all API routes
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.core.config import settings
from app.api import api_router
from app.db.session import async_engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Manages startup and shutdown events:
    - Startup: Create database tables if they don't exist
    - Shutdown: Close database connections cleanly
    
    Why: This ensures the database is ready before accepting requests
    and resources are properly cleaned up on shutdown.
    """
    # Startup: Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text("ALTER TABLE IF EXISTS materials ADD COLUMN IF NOT EXISTS source_url TEXT")
            )
    print("✓ Database tables created/verified")
    
    yield
    
    # Shutdown: cleanup
    await async_engine.dispose()
    print("✓ Database connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    description="NoCodeML API - Build ML models without code, powered by custom JWT authentication",
    version="2.0.0"
)

# CORS middleware - allows frontend to make requests to backend
# Why: Browsers block cross-origin requests by default for security.
# This middleware tells browsers it's safe for our frontend to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Root endpoint - API welcome message."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    return {"status": "healthy", "service": "NoCodeML API"}

# Include all API routes with /api/v1 prefix
# Available endpoints:
# - POST /api/v1/auth/register
# - POST /api/v1/auth/login
# - GET /api/v1/auth/me
# - POST /api/v1/auth/logout
app.include_router(api_router, prefix=settings.API_V1_STR)