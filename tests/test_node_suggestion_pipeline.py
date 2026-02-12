"""Tests for node suggestion pipeline (TDD)."""

import math
from decimal import Decimal

import pytest
import asyncio

from app.services.node_suggestions.embedding_service import EmbeddingService
from app.services.node_suggestions.ranking_service import RankingService
from app.services.node_suggestions.deduplication import deduplicate_candidates
from app.services.node_suggestions.confidence import compute_confidence
from app.services.node_suggestions.node_suggestion_service import (
    NodeSuggestionService,
)
from app.services.node_suggestions.types import (
    CandidatePhrase,
    NodeMatch,
    SuggestionRequest,
    SuggestionResult,
)


class FakeEmbeddingClient:
    def __init__(self, vector):
        self._vector = vector

    def feature_extraction(self, text, model=None):
        if isinstance(text, list):
            return [list(self._vector) for _ in text]
        return list(self._vector)


class FakeEmbeddingService(EmbeddingService):
    def __init__(self, vector):
        super().__init__(FakeEmbeddingClient(vector), expected_dim=len(vector))


class FakeKeywordService:
    def __init__(self, phrases):
        self._phrases = phrases

    def extract_phrases(self, text):
        return list(self._phrases)


class FakeRepository:
    def __init__(self, material_text, vector_matches, keyword_matches, node_titles, similarity_lookup=None):
        self.material_text = material_text
        self.vector_matches = vector_matches
        self.keyword_matches = keyword_matches
        self.node_titles = node_titles
        self.similarity_lookup = similarity_lookup or {}
        self.saved_embeddings = {}

    async def get_material_text(self, material_id):
        return self.material_text

    async def save_material_embedding(self, material_id, embedding):
        self.saved_embeddings[material_id] = embedding

    async def search_nodes_vector(self, project_id, embedding, top_k):
        return list(self.vector_matches)[:top_k]

    async def search_nodes_fts(self, project_id, query, top_k):
        return list(self.keyword_matches)[:top_k]

    async def list_nodes(self, project_id):
        return list(self.node_titles)

    async def store_suggestions(self, material_id, suggestions):
        self.suggestions = suggestions

    async def max_similarity_to_nodes(self, project_id, candidate_embedding):
        key = tuple(candidate_embedding)
        return self.similarity_lookup.get(key, 0.0)


def test_embedding_service_vector_size():
    vector = [0.1] * 768
    service = EmbeddingService(FakeEmbeddingClient(vector), expected_dim=768)
    result = service.embed_texts(["hello world"])
    assert len(result) == 1
    assert len(result[0]) == 768


def test_embedding_service_casts_decimal_values():
    class DecimalEmbeddingClient:
        def feature_extraction(self, text, model=None):
            return [Decimal("0.1")] * 768

    service = EmbeddingService(DecimalEmbeddingClient(), expected_dim=768)
    result = service.embed_texts(["hello"])
    assert isinstance(result[0][0], float)


def test_vector_results_sorted_deterministic():
    matches = [
        NodeMatch(node_id="b", score=0.7, source="vector"),
        NodeMatch(node_id="a", score=0.7, source="vector"),
        NodeMatch(node_id="c", score=0.9, source="vector"),
    ]
    ranked = RankingService.sort_by_score(matches)
    assert [match.node_id for match in ranked] == ["c", "a", "b"]


def test_hybrid_ranking_deterministic():
    semantic = {
        "node-1": 0.9,
        "node-2": 0.5,
    }
    keyword = {
        "node-1": 0.2,
        "node-2": 0.8,
    }
    ranked = RankingService.hybrid_rank(semantic, keyword, semantic_weight=0.6, keyword_weight=0.4)
    assert ranked[0].node_id == "node-1"
    assert ranked[1].node_id == "node-2"


def test_deduplicate_candidates_removes_near_duplicates():
    candidates = [
        CandidatePhrase(phrase="graph theory", embedding=[0.1] * 3),
        CandidatePhrase(phrase="stack", embedding=[0.2] * 3),
    ]
    similarity_lookup = {"graph theory": 0.8, "stack": 0.6}
    filtered = deduplicate_candidates(candidates, similarity_lookup, threshold=0.75)
    assert [item.phrase for item in filtered] == ["stack"]


def test_confidence_score_calculation():
    score = compute_confidence(coverage_score=0.6, semantic_strength=0.8)
    assert math.isclose(score, 0.7)


def test_pipeline_end_to_end_returns_suggestions():
    vector = [0.1] * 8
    embedding_service = FakeEmbeddingService(vector)
    keyword_service = FakeKeywordService(["graph", "stack", "stack"])

    repo = FakeRepository(
        material_text="graph content",
        vector_matches=[
            NodeMatch(node_id="node-1", score=0.9, source="vector"),
            NodeMatch(node_id="node-2", score=0.7, source="vector"),
        ],
        keyword_matches=[
            NodeMatch(node_id="node-2", score=0.8, source="keyword"),
            NodeMatch(node_id="node-3", score=0.4, source="keyword"),
        ],
        node_titles=["node-1", "node-2", "node-3"],
    )

    service = NodeSuggestionService(
        repository=repo,
        embedding_service=embedding_service,
        keyword_service=keyword_service,
    )

    request = SuggestionRequest(
        material_id="mat-1",
        project_id="proj-1",
        threshold=0.7,
        semantic_weight=0.6,
        keyword_weight=0.4,
        top_k=5,
    )
    result = asyncio.run(service.suggest_nodes(request))

    assert isinstance(result, SuggestionResult)
    assert result.strong
    assert result.weak
    assert result.strong[0].suggestion_type == "EXISTING"


def test_pipeline_includes_new_candidates():
    candidate_vector = [0.2] * 8
    embedding_service = FakeEmbeddingService(candidate_vector)
    keyword_service = FakeKeywordService(["new topic"])

    repo = FakeRepository(
        material_text="new topic appears once",
        vector_matches=[],
        keyword_matches=[],
        node_titles=[],
        similarity_lookup={tuple(candidate_vector): 0.2},
    )

    service = NodeSuggestionService(
        repository=repo,
        embedding_service=embedding_service,
        keyword_service=keyword_service,
    )

    request = SuggestionRequest(
        material_id="mat-2",
        project_id="proj-2",
        threshold=0.75,
        semantic_weight=0.6,
        keyword_weight=0.4,
        top_k=5,
    )

    result = asyncio.run(service.suggest_nodes(request))
    new_suggestions = [item for item in result.weak if item.suggestion_type == "NEW"]
    assert new_suggestions


def test_empty_material_returns_no_suggestions():
    embedding_service = FakeEmbeddingService([0.1] * 8)
    keyword_service = FakeKeywordService([])
    repo = FakeRepository(
        material_text="",
        vector_matches=[],
        keyword_matches=[],
        node_titles=[],
    )

    service = NodeSuggestionService(
        repository=repo,
        embedding_service=embedding_service,
        keyword_service=keyword_service,
    )

    request = SuggestionRequest(
        material_id="mat-1",
        project_id="proj-1",
        threshold=0.75,
        semantic_weight=0.6,
        keyword_weight=0.4,
        top_k=5,
    )

    result = asyncio.run(service.suggest_nodes(request))
    assert result.strong == []
    assert result.weak == []


def test_performance_ranking_large_node_set():
    matches = [
        NodeMatch(node_id=f"node-{idx}", score=1.0 - (idx / 10000), source="vector")
        for idx in range(10000)
    ]
    ranked = RankingService.sort_by_score(matches)
    assert ranked[0].score >= ranked[-1].score
