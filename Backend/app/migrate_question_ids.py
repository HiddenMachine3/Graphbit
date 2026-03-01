"""One-time migration: add question_ids column to revision_sessions."""
import asyncio
from sqlalchemy import text
from app.db.session import async_engine

async def migrate():
    async with async_engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE revision_sessions ADD COLUMN IF NOT EXISTS question_ids JSONB DEFAULT '[]'"
        ))
    print("Migration complete: question_ids column added.")

asyncio.run(migrate())
