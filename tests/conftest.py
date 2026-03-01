"""Pytest configuration to handle import paths."""

import sys
import os
from pathlib import Path
import pytest
from datetime import datetime
import asyncio
import uuid


def _load_backend_env_values(env_file: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_file.exists():
        return values

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _ensure_windows_event_loop_policy() -> None:
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add Backend directory to Python path
backend_dir = Path(__file__).parent.parent / "Backend"
sys.path.insert(0, str(backend_dir))

backend_env_values = _load_backend_env_values(backend_dir / ".env")

# Provide required settings for test imports (PostgreSQL only)
os.environ.setdefault("CELERY_BROKER_URL", backend_env_values.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))
os.environ.setdefault("CELERY_RESULT_BACKEND", backend_env_values.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"))
secret_key = os.environ.get("SECRET_KEY") or backend_env_values.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY is required in Backend/.env")
os.environ["SECRET_KEY"] = secret_key

database_url = os.environ.get("DATABASE_URL") or backend_env_values.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is required for tests and must point to PostgreSQL")
if database_url.startswith("sqlite"):
    raise RuntimeError("SQLite is disabled for tests. Configure a PostgreSQL DATABASE_URL.")
if not (database_url.startswith("postgresql://") or database_url.startswith("postgresql+")):
    raise RuntimeError("Tests require a PostgreSQL DATABASE_URL")

os.environ["DATABASE_URL"] = database_url
os.environ["POSTGRES_TEST_URL"] = database_url

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
def api_client():
    """Create a FastAPI test client using PostgreSQL in an isolated schema."""
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import NullPool

    from app.main import app
    from app.db.session import get_db
    from app.models import Base, AppUser as AppUserModel

    _ensure_windows_event_loop_policy()

    schema_name = f"test_api_{uuid.uuid4().hex[:8]}"
    engine = create_async_engine(database_url, poolclass=NullPool)
    engine = engine.execution_options(schema_translate_map={None: schema_name})
    async_session = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def init_db():
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
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

    async def drop_db():
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        await engine.dispose()

    asyncio.run(init_db())

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        asyncio.run(drop_db())
