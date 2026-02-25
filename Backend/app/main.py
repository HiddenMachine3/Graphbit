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
import os
from sqlalchemy import text
from app.core.config import settings
from app.api import api_router
from app.db.session import async_engine
from app.models import Base


def _log_hf_model_probe() -> None:
    """Log Hugging Face keyphrase model reachability to terminal only."""
    model_name = (settings.HF_KEYPHRASE_MODEL or "").strip()
    base_url = os.environ.get(
        "HF_INFERENCE_BASE_URL",
        "https://router.huggingface.co/hf-inference",
    ).rstrip("/")
    token = settings.HF_TOKEN or os.environ.get("HF_TOKEN")

    if not model_name:
        print("[HF_CHECK] Skipped: HF_KEYPHRASE_MODEL is empty.")
        return

    if not token:
        print(f"[HF_CHECK] Skipped: HF_TOKEN missing. model={model_name}")
        return

    try:
        from huggingface_hub import InferenceClient
    except Exception as exc:
        print(f"[HF_CHECK] Skipped: huggingface_hub unavailable. error={exc}")
        return

    model_target = model_name
    if not model_name.startswith(("http://", "https://")):
        model_target = f"{base_url}/models/{model_name}"

    try:
        client = InferenceClient(token=token, base_url=base_url)
        sample_text = "Depth first search explores one branch before backtracking."
        entities = client.token_classification(sample_text, model=model_target) or []
        print(f"[HF_CHECK] OK model={model_name} target={model_target} entities={len(entities)}")
    except Exception as exc:
        print(f"[HF_CHECK] FAIL model={model_name} target={model_target} error={exc}")


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
            await conn.execute(
                text("ALTER TABLE IF EXISTS materials ADD COLUMN IF NOT EXISTS transcript_text TEXT")
            )
            await conn.execute(
                text("ALTER TABLE IF EXISTS materials ADD COLUMN IF NOT EXISTS transcript_segments JSONB")
            )
    _log_hf_model_probe()
    print("✓ Database tables created/verified")
    
    yield
    
    # Shutdown: cleanup
    await async_engine.dispose()
    print("✓ Database connections closed")


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