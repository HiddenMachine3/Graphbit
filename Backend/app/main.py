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
import logging
from sqlalchemy import text
# Centralised logging — call first so all modules inherit the format
from app.core.logging_config import setup_logging
setup_logging()
# Load .env early so all modules see environment variables (GEMINI_API_KEY, etc.)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from app.core.config import settings
from app.api import api_router
from app.db.session import async_engine
from app.models import Base, AppUser as AppUserModel

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Manages startup and shutdown events:
    - Startup: Create database tables if they don't exist
    - Shutdown: Close database connections cleanly
    """
    # Startup: Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text("ALTER TABLE IF EXISTS materials ADD COLUMN IF NOT EXISTS source_url TEXT")
            )
            await conn.execute(
                text("ALTER TABLE IF EXISTS materials ADD COLUMN IF NOT EXISTS transcript_text TEXT")
            )
            await conn.execute(
                text("ALTER TABLE IF EXISTS materials ADD COLUMN IF NOT EXISTS transcript_segments JSONB")
            )
            # Enable trigram fuzzy search extension (used by /search endpoint)
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    logger.info("Database tables created/verified")

    # Seed a default AppUser if none exists (required by graph/materials/projects)
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(AppUserModel).limit(1))
        if result.scalar_one_or_none() is None:
            default_user = AppUserModel(
                id="demo-user",
                username="demo",
                name="Demo User",
                password_hash="not-used",
            )
            session.add(default_user)
            await session.commit()
            logger.info("Seeded default AppUser: id=demo-user username=demo")
    
    yield
    
    # Shutdown: cleanup
    await async_engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    description="GraphBit - Interactive knowledge graph platform for learning and collaboration",
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
    allow_origin_regex=r"^(chrome-extension|moz-extension)://.*$",
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
    return {"status": "healthy", "service": "GraphBit"}

# Include all API routes with /api/v1 prefix
# Available endpoints:
# - POST /api/v1/auth/register
# - POST /api/v1/auth/login
# - GET /api/v1/auth/me
# - POST /api/v1/auth/logout
app.include_router(api_router, prefix=settings.API_V1_STR)