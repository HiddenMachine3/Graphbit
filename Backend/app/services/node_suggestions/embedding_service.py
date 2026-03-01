"""Text embedding via Gemini Embedding API."""

import json
import logging
import os
from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import certifi

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = "text-embedding-004"
GEMINI_EMBED_DIM = 768


class EmbeddingService:
    def __init__(self, expected_dim: int = GEMINI_EMBED_DIM):
        self.expected_dim = expected_dim

    def _embed_single(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * self.expected_dim

        api_key = os.environ.get("GEMINI_API_KEY")
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
