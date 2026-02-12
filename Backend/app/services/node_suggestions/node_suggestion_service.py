import logging

from app.core.config import settings
from app.services.node_suggestions.confidence import compute_confidence
from app.services.node_suggestions.deduplication import deduplicate_candidates
from app.services.node_suggestions.ranking_service import RankingService
from app.services.node_suggestions.types import (
    CandidatePhrase,
    NodeSuggestionRepository,
    SuggestionItem,
    SuggestionRequest,
    SuggestionResult,
)
from app.services.node_suggestions.utils import chunk_text, cosine_similarity


logger = logging.getLogger(__name__)


class NodeSuggestionService:
    def __init__(self, repository: NodeSuggestionRepository, embedding_service, keyword_service):
        self.repository = repository
        self.embedding_service = embedding_service
        self.keyword_service = keyword_service

    async def suggest_nodes(self, request: SuggestionRequest) -> SuggestionResult:
        material_text = await self.repository.get_material_text(request.material_id)
        if not material_text.strip():
            logger.warning("Material %s has empty content; skipping suggestions", request.material_id)
            return SuggestionResult(strong=[], weak=[])

        material_embedding = self.embedding_service.embed_texts([material_text])[0]
        await self.repository.save_material_embedding(request.material_id, material_embedding)

        vector_matches = await self.repository.search_nodes_vector(
            request.project_id,
            material_embedding,
            request.top_k,
        )
        keyword_matches = await self.repository.search_nodes_fts(
            request.project_id,
            material_text,
            request.top_k,
        )

        semantic_scores = {match.node_id: match.score for match in vector_matches}
        keyword_scores = {match.node_id: match.score for match in keyword_matches}

        ranked = RankingService.hybrid_rank(
            semantic_scores,
            keyword_scores,
            request.semantic_weight,
            request.keyword_weight,
        )

        strong: list[SuggestionItem] = []
        weak: list[SuggestionItem] = []
        for match in ranked:
            item = SuggestionItem(
                node_id=match.node_id,
                suggested_title=None,
                suggested_description=None,
                confidence=match.score,
                suggestion_type="EXISTING",
            )
            if match.score >= request.threshold:
                strong.append(item)
            else:
                weak.append(item)

        candidate_phrases = self.keyword_service.extract_phrases(material_text)
        chunks = chunk_text(material_text)
        total_chunks = max(len(chunks), 1)

        candidate_embeddings = []
        if candidate_phrases:
            candidate_embeddings = self.embedding_service.embed_texts(candidate_phrases)

        candidates: list[CandidatePhrase] = [
            CandidatePhrase(phrase=phrase, embedding=embedding)
            for phrase, embedding in zip(candidate_phrases, candidate_embeddings)
        ]

        similarity_lookup = {}
        for candidate in candidates:
            similarity_lookup[candidate.phrase] = await self.repository.max_similarity_to_nodes(
                request.project_id,
                candidate.embedding,
            )

        candidates = deduplicate_candidates(
            candidates,
            similarity_lookup,
            threshold=settings.SUGGESTION_DEDUP_THRESHOLD,
        )

        for candidate in candidates:
            coverage = sum(
                1 for chunk in chunks if candidate.phrase.lower() in chunk.lower()
            ) / total_chunks
            semantic_strength = cosine_similarity(candidate.embedding, material_embedding)
            confidence = compute_confidence(coverage, semantic_strength)
            weak.append(
                SuggestionItem(
                    node_id=None,
                    suggested_title=candidate.phrase,
                    suggested_description=None,
                    confidence=confidence,
                    suggestion_type="NEW",
                )
            )

        await self.repository.store_suggestions(request.material_id, strong + weak)

        return SuggestionResult(strong=strong, weak=weak)
