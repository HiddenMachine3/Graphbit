"""Topic extraction for transcript text — Gemini-first with keyword fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from typing import Iterable

import requests
import certifi

logger = logging.getLogger(__name__)


def extract_topics_from_text(
    text: str,
    title: str | None = None,
    max_topics: int = 15,
) -> list[str]:
    """Extract topic labels from text.

    Uses Gemini API if GEMINI_API_KEY is set.
    Falls back to keyword extraction otherwise.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        topics = _extract_topics_with_gemini(
            text, title=title, max_topics=max_topics, api_key=gemini_key
        )
        if topics:
            logger.info("Topics extracted via Gemini: count=%d", len(topics))
            return topics
        logger.warning("Gemini returned no topics, falling back to keywords")

    else:
        logger.info("GEMINI_API_KEY not set, using keyword fallback")
    return _extract_topics_fallback(text, max_topics=max_topics)


def _extract_topics_with_gemini(
    text: str,
    title: str | None,
    max_topics: int,
    api_key: str,
) -> list[str]:
    """Extract topics using Gemini API with structured JSON output."""
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            }
        },
        "required": ["topics"],
    }

    prompt = (
        "You extract concise study topics from lecture transcripts.\n"
        "Return JSON only with a list of topics.\n\n"
        f"Title: {title or 'Unknown'}\n"
        "Transcript:\n"
        f"{text}\n\n"
        "IMPORTANT: Only return topics that are genuinely distinct and "
        "important concepts from this content. Do NOT pad with generic or "
        "tangential topics. Quality over quantity.\n"
        f"Return between 3 and {max_topics} topics, based on the actual "
        "content richness."
    )

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
            "response_mime_type": "application/json",
            "response_schema": schema,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        resp = requests.post(endpoint, json=body, timeout=20, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()

        raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw_json)
        topics = parsed.get("topics", [])
        return _clean_topics(topics, max_topics=max_topics)
    except Exception as exc:
        logger.exception("Gemini topic extraction failed: %s", exc)
        return []


def _extract_topics_fallback(text: str, max_topics: int) -> list[str]:
    words = _tokenize(text)
    counts = Counter(words)
    most_common = [word for word, _ in counts.most_common(max_topics * 2)]
    topics = []
    for word in most_common:
        if word not in topics:
            topics.append(word.title())
        if len(topics) >= max_topics:
            break
    return topics


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = [word for word in cleaned.split() if word not in _stop_words()]
    return [word for word in words if 3 <= len(word) <= 24]


def _stop_words() -> set[str]:
    return {
        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "your",
        "you",
        "are",
        "was",
        "were",
        "have",
        "has",
        "had",
        "but",
        "not",
        "can",
        "could",
        "will",
        "would",
        "into",
        "over",
        "under",
        "between",
        "about",
        "their",
        "there",
        "what",
        "when",
        "where",
        "which",
        "while",
        "also",
        "than",
        "then",
        "them",
        "they",
        "use",
        "using",
        "used",
    }


def _clean_topics(topics: Iterable[str], max_topics: int) -> list[str]:
    cleaned: list[str] = []
    for topic in topics:
        value = str(topic).strip()
        if not value:
            continue
        if value.lower() not in {t.lower() for t in cleaned}:
            cleaned.append(value)
        if len(cleaned) >= max_topics:
            break
    return cleaned
