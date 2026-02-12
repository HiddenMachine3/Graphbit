from app.services.node_suggestions.types import NodeMatch


class RankingService:
    @staticmethod
    def normalize_weights(semantic_weight: float, keyword_weight: float) -> tuple[float, float]:
        total = semantic_weight + keyword_weight
        if total <= 0:
            return 0.6, 0.4
        return semantic_weight / total, keyword_weight / total

    @staticmethod
    def sort_by_score(matches: list[NodeMatch]) -> list[NodeMatch]:
        return sorted(matches, key=lambda match: (-match.score, match.node_id))

    @staticmethod
    def hybrid_rank(
        semantic_scores: dict[str, float],
        keyword_scores: dict[str, float],
        semantic_weight: float,
        keyword_weight: float,
    ) -> list[NodeMatch]:
        semantic_weight, keyword_weight = RankingService.normalize_weights(
            semantic_weight, keyword_weight
        )
        combined: list[NodeMatch] = []
        for node_id in sorted(set(semantic_scores) | set(keyword_scores)):
            semantic = semantic_scores.get(node_id, 0.0)
            keyword = keyword_scores.get(node_id, 0.0)
            score = semantic_weight * semantic + keyword_weight * keyword
            combined.append(NodeMatch(node_id=node_id, score=score, source="hybrid"))
        return RankingService.sort_by_score(combined)
