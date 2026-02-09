"""Pytest configuration to handle import paths."""

import sys
import os
from pathlib import Path
import pytest
from datetime import datetime
import asyncio

# Add Backend directory to Python path
backend_dir = Path(__file__).parent.parent / "Backend"
sys.path.insert(0, str(backend_dir))

# Provide required settings for test imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")

# Create 'backend' namespace module that points to 'app'
class BackendNamespace:
    app = None

sys.modules['backend'] = sys.modules['sys']

# Import app module first
import app as app_module
sys.modules['backend.app'] = app_module

# Also make submodules accessible
from app import domain
sys.modules['backend.app.domain'] = domain


# ============================================================
# TEST FIXTURES
# ============================================================


@pytest.fixture
def test_project_id():
    """Default test project ID."""
    return "test_project_1"


@pytest.fixture
def test_project():
    """Create a test project."""
    from backend.app.domain import Project, ProjectVisibility
    return Project(
        id="test_project_1",
        name="Test Project",
        description="A test project for unit tests",
        owner_id="test_user_1",
        visibility=ProjectVisibility.PRIVATE,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def api_client(tmp_path):
    """Create a FastAPI test client with an isolated SQLite database."""
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    from app.main import app
    from app.db.session import get_db
    from app.models import Base, AppUser as AppUserModel

    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async_session = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_session() as session:
            admin = AppUserModel(
                id="admin",
                username="admin",
                name="admin",
                password_hash="admin",
            )
            session.add(admin)
            await session.commit()

    asyncio.run(init_db())

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
