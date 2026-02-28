import os

import pytest

from app.services.node_suggestions.keyword_extraction_service import KeywordExtractionService


class DummyResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_gemini_keyword_extraction(monkeypatch):
    # Mock requests.post to return generateContent-style response
    def fake_post(url, json=None, timeout=None):
        payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": __import__('json').dumps({"phrases": ["Graph Theory", "Algorithms"]})}
                        ]
                    }
                }
            ]
        }
        return DummyResp(payload)

    monkeypatch.setattr("requests.post", fake_post)

    service = KeywordExtractionService(client=None)
    # Call the Gemini helper directly with a test API key
    phrases = service._extract_with_gemini("This text mentions Graph Theory and Algorithms.", api_key="test-key")

    assert isinstance(phrases, list)
    assert len(phrases) >= 1
    for p in phrases:
        assert isinstance(p, str)
