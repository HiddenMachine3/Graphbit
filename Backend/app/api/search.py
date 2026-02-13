"""Search API endpoints for nodes and materials."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Material as MaterialModel, Node as NodeModel


router = APIRouter()


@router.get("/search")
async def search_knowledge(
    project_id: str = Query(..., min_length=1),
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search nodes and materials for a project using Postgres fuzzy matching."""
    query = q.strip()
    pattern = f"%{query}%"

    if db.bind.dialect.name == "postgresql":
        try:
            await db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        except Exception:
            pass

        node_rows = await db.execute(
            text(
                """
                SELECT id, topic_name AS title, similarity(topic_name, :q) AS score
                FROM nodes
                WHERE project_id = :project_id
                  AND (topic_name ILIKE :pattern OR similarity(topic_name, :q) > 0.2)
                ORDER BY score DESC
                LIMIT :limit
                """
            ),
            {
                "project_id": project_id,
                "q": query,
                "pattern": pattern,
                "limit": limit,
            },
        )
        nodes = [
            {"id": row.id, "title": row.title, "score": float(row.score or 0)}
            for row in node_rows
        ]

        material_rows = await db.execute(
            text(
                """
                SELECT id, title, similarity(title, :q) AS score
                FROM materials
                WHERE project_id = :project_id
                  AND (
                    title ILIKE :pattern
                    OR content_text ILIKE :pattern
                                        OR COALESCE(transcript_text, '') ILIKE :pattern
                    OR similarity(title, :q) > 0.2
                  )
                ORDER BY score DESC
                LIMIT :limit
                """
            ),
            {
                "project_id": project_id,
                "q": query,
                "pattern": pattern,
                "limit": limit,
            },
        )
        materials = [
            {"id": row.id, "title": row.title, "score": float(row.score or 0)}
            for row in material_rows
        ]
    else:
        node_rows = await db.execute(
            select(NodeModel.id, NodeModel.topic_name)
            .where(
                NodeModel.project_id == project_id,
                NodeModel.topic_name.ilike(pattern),
            )
            .limit(limit)
        )
        nodes = [
            {"id": row.id, "title": row.topic_name, "score": 0.0}
            for row in node_rows
        ]

        material_rows = await db.execute(
            select(MaterialModel.id, MaterialModel.title)
            .where(
                MaterialModel.project_id == project_id,
                or_(
                    MaterialModel.title.ilike(pattern),
                    MaterialModel.content_text.ilike(pattern),
                    MaterialModel.transcript_text.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        materials = [
            {"id": row.id, "title": row.title, "score": 0.0}
            for row in material_rows
        ]

    return {"nodes": nodes, "materials": materials}