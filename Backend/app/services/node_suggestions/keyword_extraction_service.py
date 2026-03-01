"""Keyword/keyphrase extraction via Gemini structured output."""

import json
import logging
import os
from typing import Any

import certifi
import requests

logger = logging.getLogger(__name__)


class KeywordExtractionService:
    def __init__(self, client: Any = None, api_key: str | None = None):
        self._client = client
        self._api_key = api_key

    def extract_phrases(self, text: str) -> list[str]:
        if not text.strip():
            return []

        gemini_key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is not set for keyword extraction")

        return self._extract_with_gemini(text, api_key=gemini_key)

    def _extract_with_gemini(self, text: str, api_key: str | None = None) -> list[str]:
        resolved_api_key = api_key or self._api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set for keyword extraction")

        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={resolved_api_key}"
        )

        schema = {
            "type": "object",
            "properties": {
                "phrases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                }
            },
            "required": ["phrases"],
        }

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"Extract concise key phrases from the following text:\n\n{text}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1024,
                "response_mime_type": "application/json",
                "response_schema": schema,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        post_func = self._client.post if self._client and hasattr(self._client, "post") else requests.post
        resp = post_func(endpoint, json=body, timeout=20, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()

        try:
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_json)
        except Exception:
            raise RuntimeError(f"Gemini returned invalid structured response: {data}")

        phrases = parsed.get("phrases")
        if not isinstance(phrases, list):
            raise RuntimeError("Schema violation: 'phrases' missing or not array")

        normalized = []
        seen = set()
        for phrase in phrases:
            cleaned = str(phrase).strip().lower()
            if len(cleaned) < 3 or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized
