"""Topic extraction for transcript text."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Iterable


def extract_topics_from_text(
    text: str,
    title: str | None = None,
    max_topics: int = 8,
) -> list[str]:
    """Extract topic labels from text.

    Uses a local HF model if configured, otherwise OpenAI if OPENAI_API_KEY is set.
    Falls back to keyword extraction otherwise.
    """
    hf_model_name = os.getenv("HF_TOPIC_MODEL")
    if hf_model_name:
        topics = _extract_topics_with_local_model(
            text, title=title, max_topics=max_topics, model_name=hf_model_name
        )
        if topics:
            return topics

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        topics = _extract_topics_with_llm(text, title=title, max_topics=max_topics)
        if topics:
            return topics

    return _extract_topics_fallback(text, max_topics=max_topics)


def _extract_topics_with_llm(
    text: str,
    title: str | None,
    max_topics: int,
) -> list[str]:
    prompt = (
        "You extract concise study topics from lecture transcripts.\n"
        "Return JSON only with a list of topics.\n\n"
        f"Title: {title or 'Unknown'}\n"
        "Transcript:\n"
        f"{text}\n\n"
        f"Respond with: {{\"topics\": [\"Topic 1\", ...]}} (max {max_topics})"
    )

    try:
        import openai

        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
        topics = result.get("topics", [])
        return _clean_topics(topics, max_topics=max_topics)
    except Exception:
        return []


def _extract_topics_with_local_model(
    text: str,
    title: str | None,
    max_topics: int,
    model_name: str,
) -> list[str]:
    prompt = (
        "You extract concise study topics from lecture transcripts. "
        "Return JSON only with a list of topics.\n\n"
        f"Title: {title or 'Unknown'}\n"
        "Transcript:\n"
        f"{text}\n\n"
        f"Respond with: {{\"topics\": [\"Topic 1\", ...]}} (max {max_topics})"
    )

    try:
        tokenizer, model = _get_local_model(model_name)
        messages = [{"role": "user", "content": prompt}]
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=200, do_sample=False)
        generated = tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[-1] :],
            skip_special_tokens=True,
        )
        topics = _parse_topics_from_json(generated)
        return _clean_topics(topics, max_topics=max_topics)
    except Exception:
        return []


_LOCAL_MODEL_CACHE: tuple[object, object] | None = None
_LOCAL_MODEL_NAME: str | None = None


def _get_local_model(model_name: str) -> tuple[object, object]:
    global _LOCAL_MODEL_CACHE, _LOCAL_MODEL_NAME
    if _LOCAL_MODEL_CACHE and _LOCAL_MODEL_NAME == model_name:
        return _LOCAL_MODEL_CACHE

    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype="auto",
    )
    _LOCAL_MODEL_CACHE = (tokenizer, model)
    _LOCAL_MODEL_NAME = model_name
    return _LOCAL_MODEL_CACHE


def _parse_topics_from_json(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
        return parsed.get("topics", []) if isinstance(parsed, dict) else []
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return []
        try:
            parsed = json.loads(match.group(0))
            return parsed.get("topics", []) if isinstance(parsed, dict) else []
        except Exception:
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
