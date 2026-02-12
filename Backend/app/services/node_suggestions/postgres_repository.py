from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Material as MaterialModel, Node as NodeModel, MaterialNodeSuggestion
from app.services.node_suggestions.types import NodeMatch, SuggestionItem


class PostgresNodeSuggestionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_material_text(self, material_id: str) -> str:
        result = await self.db.execute(
            select(MaterialModel.content_text).where(MaterialModel.id == material_id)
        )
        return result.scalar_one_or_none() or ""

    async def save_material_embedding(self, material_id: str, embedding: list[float]) -> None:
        result = await self.db.execute(
            select(MaterialModel).where(MaterialModel.id == material_id)
        )
        material = result.scalar_one_or_none()
        if material:
            material.embedding = embedding
        await self.db.commit()

    async def search_nodes_vector(self, project_id: str, embedding: list[float], top_k: int) -> list[NodeMatch]:
        if self.db.bind.dialect.name != "postgresql":
            return []
        query = text(
            "SELECT id, 1 - (embedding <=> CAST(:embedding AS vector)) AS score "
            "FROM nodes "
            "WHERE project_id = :project_id AND embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:embedding AS vector) "
            "LIMIT :top_k"
        )
        result = await self.db.execute(
            query,
            {"embedding": embedding, "project_id": project_id, "top_k": top_k},
        )
        return [
            NodeMatch(node_id=row[0], score=float(row[1]), source="vector")
            for row in result.fetchall()
        ]

    async def search_nodes_fts(self, project_id: str, query_text: str, top_k: int) -> list[NodeMatch]:
        if self.db.bind.dialect.name != "postgresql":
            return []
        query = text(
            "SELECT id, ts_rank(search_vector, plainto_tsquery('english', :query)) AS score "
            "FROM nodes "
            "WHERE project_id = :project_id AND search_vector IS NOT NULL "
            "ORDER BY score DESC "
            "LIMIT :top_k"
        )
        result = await self.db.execute(
            query,
            {"project_id": project_id, "query": query_text, "top_k": top_k},
        )
        return [
            NodeMatch(node_id=row[0], score=float(row[1]), source="keyword")
            for row in result.fetchall()
        ]

    async def list_nodes(self, project_id: str) -> list[str]:
        result = await self.db.execute(
            select(NodeModel.id).where(NodeModel.project_id == project_id)
        )
        return [row[0] for row in result.fetchall()]

    async def store_suggestions(self, material_id: str, suggestions: list[SuggestionItem]) -> None:
        now_id_prefix = f"suggestion-{int(datetime.now().timestamp() * 1000)}"
        existing = await self.db.execute(
            select(MaterialNodeSuggestion).where(
                MaterialNodeSuggestion.material_id == material_id
            )
        )
        for suggestion in existing.scalars().all():
            await self.db.delete(suggestion)

        for index, item in enumerate(suggestions):
            suggestion = MaterialNodeSuggestion(
                id=f"{now_id_prefix}-{index}",
                material_id=material_id,
                node_id=item.node_id,
                suggested_title=item.suggested_title,
                suggested_description=item.suggested_description,
                confidence=item.confidence,
                suggestion_type=item.suggestion_type,
            )
            self.db.add(suggestion)

        await self.db.commit()

    async def max_similarity_to_nodes(self, project_id: str, candidate_embedding: list[float]) -> float:
        if self.db.bind.dialect.name != "postgresql":
            return 0.0
        query = text(
            "SELECT MAX(1 - (embedding <=> CAST(:embedding AS vector))) AS score "
            "FROM nodes "
            "WHERE project_id = :project_id AND embedding IS NOT NULL"
        )
        result = await self.db.execute(
            query,
            {"embedding": candidate_embedding, "project_id": project_id},
        )
        score = result.scalar_one_or_none()
        return float(score or 0.0)
