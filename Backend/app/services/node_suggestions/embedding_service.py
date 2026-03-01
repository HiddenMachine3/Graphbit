"""Text embedding via Gemini Embedding API."""

import logging
import os
from typing import Any
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import certifi

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = "gemini-embedding-001"
GEMINI_EMBED_DIM = 768


class EmbeddingService:
    def __init__(
        self,
        client: Any = None,
        expected_dim: int = GEMINI_EMBED_DIM,
        api_key: str | None = None,
    ):
        if isinstance(client, int) and expected_dim == GEMINI_EMBED_DIM:
            expected_dim = client
            client = None

        self._client = client
        self.expected_dim = expected_dim
        self._api_key = api_key

    def _embed_single(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * self.expected_dim

        if self._client and hasattr(self._client, "feature_extraction"):
            raw_vector = self._client.feature_extraction(text, model=None)
            if raw_vector and isinstance(raw_vector[0], list):
                raw_vector = raw_vector[0]
            embedding = [float(v) for v in raw_vector]

            if len(embedding) != self.expected_dim:
                if len(embedding) > self.expected_dim:
                    embedding = embedding[:self.expected_dim]
                else:
                    raise ValueError(
                        f"Expected embedding size {self.expected_dim}, got {len(embedding)}"
                    )
            return embedding

        api_key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        model = os.environ.get("GEMINI_EMBED_MODEL", GEMINI_EMBED_MODEL)
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:embedContent?key={api_key}"
        )

        body = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": text[:8000]}]},
        }

        resp = requests.post(endpoint, json=body, timeout=20, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()

        embedding = data.get("embedding", {}).get("values", [])
        if not embedding:
            raise RuntimeError(f"Gemini embedding returned empty result: {data}")

        if len(embedding) != self.expected_dim:
            if len(embedding) > self.expected_dim:
                embedding = embedding[:self.expected_dim]
            else:
                raise ValueError(
                    f"Expected embedding size {self.expected_dim}, got {len(embedding)}"
                )

        return [float(v) for v in embedding]

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        if not texts_list:
            return []

        # Single text: skip threading overhead
        if len(texts_list) == 1:
            return [self._embed_single(texts_list[0])]

        # Multiple texts: embed in parallel threads
        max_workers = min(len(texts_list), 8)
        vectors: list[list[float] | None] = [None] * len(texts_list)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self._embed_single, text): i
                for i, text in enumerate(texts_list)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                vectors[idx] = future.result()

        return vectors
