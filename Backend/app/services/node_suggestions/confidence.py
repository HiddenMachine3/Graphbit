def compute_confidence(coverage_score: float, semantic_strength: float) -> float:
    return 0.5 * coverage_score + 0.5 * semantic_strength
