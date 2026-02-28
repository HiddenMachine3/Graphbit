"""
Live integration test for Gemini keyword extraction.

Requires GEMINI_API_KEY to be set in the environment (or backend/.env).
Calls the real Gemini API — no mocks, no dummy data.
"""

import os
import sys

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

# Load backend/.env so GEMINI_API_KEY is available
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

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
