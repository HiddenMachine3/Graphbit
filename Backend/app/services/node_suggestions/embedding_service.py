from typing import Iterable
import os

from app.core.config import settings


class EmbeddingService:
    def __init__(self, client, expected_dim: int):
        self.client = client
        self.expected_dim = expected_dim

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        vectors = []
        model_name = getattr(settings, "HF_EMBED_MODEL", None)
        base_url = os.environ.get(
            "HF_INFERENCE_BASE_URL",
            "https://router.huggingface.co/hf-inference",
        ).rstrip("/")
        model_target = model_name
        if model_name and isinstance(model_name, str) and not model_name.startswith(("http://", "https://")):
            model_target = f"{base_url}/models/{model_name}"
        for text in texts:
            if not text:
                vectors.append([0.0] * self.expected_dim)
                continue
            result = self.client.feature_extraction(text, model=model_target)
            if isinstance(result, list) and result and isinstance(result[0], list):
                vector = result[0]
            else:
                vector = result
            if len(vector) != self.expected_dim:
                raise ValueError(
                    f"Expected embedding size {self.expected_dim}, got {len(vector)}"
                )
            vectors.append([float(value) for value in vector])
        return vectors
