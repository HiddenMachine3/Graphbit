"""
Live integration test for Gemini keyword extraction.

Requires GEMINI_API_KEY to be set in the environment (or backend/.env).
Calls the real Gemini API — no mocks, no dummy data.
"""

import os
import sys
from pathlib import Path

import pytest
import requests

pytestmark = pytest.mark.live

# Ensure the backend package is importable
project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "Backend"
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load backend/.env so GEMINI_API_KEY is available
load_dotenv(backend_dir / ".env")

from app.services.node_suggestions.keyword_extraction_service import KeywordExtractionService


@pytest.fixture
def api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY not set — skipping live Gemini test")
    return key


@pytest.fixture
def service():
    return KeywordExtractionService(client=None)


SAMPLE_TEXT = (
    "Photosynthesis is the process by which green plants convert sunlight, "
    "water, and carbon dioxide into glucose and oxygen. It occurs mainly in "
    "the chloroplasts of leaf cells and is essential for life on Earth."
)


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class TestGeminiLive:
    """Live tests that hit the real Gemini API — no mocks."""

    def test_extract_with_gemini_returns_list_of_strings(self, service, api_key):
        """Verify _extract_with_gemini returns a non-empty list of lowercase strings."""
        result = service._extract_with_gemini(SAMPLE_TEXT, api_key=api_key)

        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) >= 1, "Expected at least one extracted phrase"

        for phrase in result:
            assert isinstance(phrase, str), f"Each phrase must be a string, got {type(phrase)}"
            assert phrase == phrase.strip().lower(), (
                f"Phrase should be stripped and lowercase: '{phrase}'"
            )
            assert len(phrase) >= 3, f"Phrase too short (< 3 chars): '{phrase}'"

    def test_no_duplicate_phrases(self, service, api_key):
        """Verify returned phrases contain no duplicates."""
        result = service._extract_with_gemini(SAMPLE_TEXT, api_key=api_key)

        assert len(result) == len(set(result)), (
            f"Duplicate phrases found: {result}"
        )

    def test_relevant_phrases_extracted(self, service, api_key):
        """Verify at least one domain-relevant phrase appears in the output."""
        result = service._extract_with_gemini(SAMPLE_TEXT, api_key=api_key)

        joined = " ".join(result)
        relevant_terms = ["photosynthesis", "chloroplast", "glucose", "oxygen", "sunlight", "carbon dioxide"]
        found = [t for t in relevant_terms if t in joined]

        assert len(found) >= 1, (
            f"Expected at least one of {relevant_terms} in extracted phrases {result}"
        )

    def test_different_input_gives_different_output(self, service, api_key):
        """Verify the model actually reads the input (not returning a canned response)."""
        result_bio = service._extract_with_gemini(SAMPLE_TEXT, api_key=api_key)

        cs_text = (
            "A binary search tree is a data structure that maintains sorted order. "
            "Insertion, deletion, and lookup operations run in O(log n) average time."
        )
        result_cs = service._extract_with_gemini(cs_text, api_key=api_key)

        assert result_bio != result_cs, (
            "Two completely different inputs produced identical output — API may not be working correctly"
        )

    def test_list_models_includes_embedding_capability(self, api_key):
        """Verify Gemini models endpoint is reachable and has embedding-capable models."""
        url = f"{GEMINI_API_BASE}?key={api_key}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        payload = response.json()
        models = payload.get("models", [])
        assert isinstance(models, list), "Expected 'models' to be a list"
        assert len(models) > 0, "Expected at least one model from Gemini models endpoint"

        embedding_capable = [
            model
            for model in models
            if "embedContent" in model.get("supportedGenerationMethods", [])
            or "embed" in model.get("name", "").lower()
        ]
        assert embedding_capable, "Expected at least one embedding-capable model"

    def test_embedding_endpoint_smoke_for_known_models(self, api_key):
        """Verify at least one known embedding model can embed text successfully."""
        candidate_models = ["text-embedding-004", "embedding-001"]
        successful_models: list[str] = []

        for model in candidate_models:
            url = f"{GEMINI_API_BASE}/{model}:embedContent?key={api_key}"
            body = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": "Hello world"}]},
            }
            response = requests.post(url, json=body, timeout=20)
            if response.status_code == 200:
                data = response.json()
                values = data.get("embedding", {}).get("values", [])
                assert isinstance(values, list) and len(values) > 0, (
                    f"Expected non-empty embedding values for {model}, got: {data}"
                )
                successful_models.append(model)

        assert successful_models, (
            "None of the known embedding models returned success: "
            f"{candidate_models}"
        )
