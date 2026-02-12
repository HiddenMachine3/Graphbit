from app.services.node_suggestions.types import CandidatePhrase


def deduplicate_candidates(
    candidates: list[CandidatePhrase],
    similarity_lookup: dict[str, float],
    threshold: float,
) -> list[CandidatePhrase]:
    filtered: list[CandidatePhrase] = []
    for candidate in candidates:
        similarity = similarity_lookup.get(candidate.phrase, 0.0)
        if similarity >= threshold:
            continue
        filtered.append(candidate)
    return filtered
