from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class NodeMatch:
    node_id: str
    score: float
    source: str


@dataclass(frozen=True)
class CandidatePhrase:
    phrase: str
    embedding: list[float]


@dataclass(frozen=True)
class SuggestionItem:
    node_id: Optional[str]
    suggested_title: Optional[str]
    suggested_description: Optional[str]
    confidence: float
    suggestion_type: str


@dataclass(frozen=True)
class SuggestionRequest:
    material_id: str
    project_id: str
    threshold: float
    semantic_weight: float
    keyword_weight: float
    top_k: int


@dataclass(frozen=True)
class SuggestionResult:
    strong: list[SuggestionItem]
    weak: list[SuggestionItem]


class NodeSuggestionRepository(Protocol):
    async def get_material_text(self, material_id: str) -> str:
        ...

    async def save_material_embedding(self, material_id: str, embedding: list[float]) -> None:
        ...

    async def search_nodes_vector(self, project_id: str, embedding: list[float], top_k: int) -> list[NodeMatch]:
        ...

    async def search_nodes_fts(self, project_id: str, query: str, top_k: int) -> list[NodeMatch]:
        ...

    async def list_nodes(self, project_id: str) -> list[str]:
        ...

    async def store_suggestions(self, material_id: str, suggestions: list[SuggestionItem]) -> None:
        ...

    async def max_similarity_to_nodes(self, project_id: str, candidate_embedding: list[float]) -> float:
        ...
