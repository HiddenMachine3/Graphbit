import math


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must be the same length")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str, min_tokens: int = 500, max_tokens: int = 800) -> list[str]:
    words = [word for word in text.split() if word]
    if not words:
        return []
    chunk_size = max(min_tokens, min(max_tokens, len(words)))
    chunks = []
    for start in range(0, len(words), chunk_size):
        chunk = " ".join(words[start:start + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks
