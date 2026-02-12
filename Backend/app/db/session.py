from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from typing import AsyncGenerator

database_url = settings.DATABASE_URL.strip().lower()
if database_url.startswith("sqlite"):
    raise RuntimeError("SQLite is disabled for this project. Use PostgreSQL DATABASE_URL.")
if not (
    database_url.startswith("postgresql://")
    or database_url.startswith("postgresql+")
):
    raise RuntimeError("Unsupported DATABASE_URL. PostgreSQL is required.")

async_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        yield session