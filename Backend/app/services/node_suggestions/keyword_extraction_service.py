import logging
import os
import json
from typing import Any

import certifi
import requests

from app.core.config import settings


logger = logging.getLogger(__name__)


class KeywordExtractionService:
    def __init__(self, client):
        self.client = client

    def extract_phrases(self, text: str) -> list[str]:
        if not text.strip():
            return []

        # Prefer Gemini structured extraction when API key is provided.
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                gemini_extracted = self._extract_with_gemini(text, api_key=gemini_key)
                print("Wordkd :", gemini_extracted)
                return gemini_extracted
            except Exception:
                print("Gemini keyword extraction failed, falling back to HF")
                logger.exception("Gemini keyword extraction failed, falling back to HF")
        else:
            print("GEMINI KEY not found")
        # Fallback to Hugging Face inference client behavior
        model_name = getattr(settings, "HF_KEYPHRASE_MODEL", None)
        base_url = os.environ.get(
            "HF_INFERENCE_BASE_URL",
            "https://router.huggingface.co/hf-inference",
        ).rstrip("/")
        model_target = model_name
        if model_name and isinstance(model_name, str) and not model_name.startswith(("http://", "https://")):
            model_target = f"{base_url}/models/{model_name}"
        try:
            results = self.client.token_classification(
                text,
                model=model_target,
            )
        except Exception as exc:
            logger.exception(
                "Keyword extraction model call failed. model=%s target=%s",
                model_name,
                model_target,
            )
            raise RuntimeError(f"HF keyword extraction failed for model '{model_name}': {exc}") from exc

        return self._normalize_hf_results(results)


    def _extract_with_gemini(self, text: str, api_key: str) -> list[str]:
        # v1beta is required for structured output (response_mime_type / response_schema)
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

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

        resp = requests.post(endpoint, json=body, timeout=20, verify=certifi.where())
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

    def _normalize_hf_results(self, results: list[dict]) -> list[str]:
        phrases: list[str] = []
        current = ""
        for item in results or []:
            word = item.get("word", "")
            if not word:
                continue
            if word.startswith("##"):
                current += word.replace("##", "")
                continue
            if current:
                phrases.append(current)
            current = word
        if current:
            phrases.append(current)

        normalized = []
        seen = set()
        for phrase in phrases:
            cleaned = phrase.strip().lower()
            if len(cleaned) < 3 or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized
