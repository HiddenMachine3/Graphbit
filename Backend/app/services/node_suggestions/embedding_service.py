from typing import Iterable
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.config import settings


class EmbeddingService:
    def __init__(self, client, expected_dim: int):
        self.client = client
        self.expected_dim = expected_dim

    def _resolve_model_target(self) -> str:
        model_name = getattr(settings, "HF_EMBED_MODEL", None)
        base_url = os.environ.get(
            "HF_INFERENCE_BASE_URL",
            "https://router.huggingface.co/hf-inference",
        ).rstrip("/")
        model_target = model_name
        if model_name and isinstance(model_name, str) and not model_name.startswith(("http://", "https://")):
            model_target = f"{base_url}/models/{model_name}"
        return model_target

    def _embed_single(self, text: str, model_target: str) -> list[float]:
        if not text:
            return [0.0] * self.expected_dim
        result = self.client.feature_extraction(text, model=model_target)
        if isinstance(result, list) and result and isinstance(result[0], list):
            vector = result[0]
        else:
            vector = result
        if len(vector) != self.expected_dim:
            raise ValueError(
                f"Expected embedding size {self.expected_dim}, got {len(vector)}"
            )
        return [float(value) for value in vector]

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        if not texts_list:
            return []

        model_target = self._resolve_model_target()

        # Single text: skip threading overhead
        if len(texts_list) == 1:
            return [self._embed_single(texts_list[0], model_target)]

        # Multiple texts: embed in parallel threads
        max_workers = min(len(texts_list), 8)
        vectors: list[list[float] | None] = [None] * len(texts_list)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._embed_single, text, model_target): i
                for i, text in enumerate(texts_list)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                vectors[idx] = future.result()  # propagates exceptions

        return vectors
