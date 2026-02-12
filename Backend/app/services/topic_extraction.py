"""Topic extraction for transcript text."""

from __future__ import annotations

import json
import os
import re
from typing import Iterable


class TopicExtractionError(Exception):
    """Raised when topic extraction fails — no fallback, no fake results."""
    pass


def extract_topics_from_text(
    text: str,
    title: str | None = None,
    max_topics: int = 8,
) -> list[str]:
    """Extract topic labels from text using a local HF model.

    Raises TopicExtractionError if the model fails — never returns fake results.
    """
    hf_model_name = os.getenv("HF_TOPIC_MODEL", "Qwen/Qwen2.5-7B-Instruct")

    topics = _extract_topics_with_local_model(
        text, title=title, max_topics=max_topics, model_name=hf_model_name
    )
    if topics:
        return topics

    raise TopicExtractionError(
        f"Topic extraction failed: the local model ({hf_model_name}) "
        "returned no topics. Check the server logs for details."
    )


def _extract_topics_with_local_model(
    text: str,
    title: str | None,
    max_topics: int,
    model_name: str,
) -> list[str]:
    # Truncate transcript to ~6000 words (~8k tokens) to fit context window.
    # Sample from start and end to capture introduction + conclusion topics.
    words = text.split()
    max_words = 6000
    if len(words) > max_words:
        half = max_words // 2
        truncated = " ".join(words[:half]) + "\n\n[...]\n\n" + " ".join(words[-half:])
    else:
        truncated = text

    prompt = (
        "You are a study-topic extractor. Given a lecture transcript, "
        "identify the key study topics or concepts discussed.\n"
        "Return ONLY valid JSON: {\"topics\": [\"Topic 1\", \"Topic 2\", ...]}\n"
        "Each topic should be 1-4 words. No explanations.\n\n"
        f"Title: {title or 'Unknown'}\n\n"
        f"Transcript:\n{truncated}\n\n"
        f"Extract up to {max_topics} concise study topics as JSON:"
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
    except TopicExtractionError:
        raise
    except Exception as exc:
        import traceback
        print(f"[topic_extraction] Local model error: {exc}")
        traceback.print_exc()
        raise TopicExtractionError(
            f"Local model ({model_name}) failed: {exc}"
        ) from exc


_LOCAL_MODEL_CACHE: tuple[object, object] | None = None
_LOCAL_MODEL_NAME: str | None = None


def _get_local_model(model_name: str) -> tuple[object, object]:
    global _LOCAL_MODEL_CACHE, _LOCAL_MODEL_NAME
    if _LOCAL_MODEL_CACHE and _LOCAL_MODEL_NAME == model_name:
        return _LOCAL_MODEL_CACHE

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[topic_extraction] Loading model {model_name}…")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    has_cuda = torch.cuda.is_available()
    load_kwargs: dict = {}
    if has_cuda:
        load_kwargs["device_map"] = "auto"
        load_kwargs["torch_dtype"] = "auto"
    else:
        # CPU-only: use float32 (bfloat16 is slow on most CPUs)
        load_kwargs["torch_dtype"] = torch.float32

    model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
    print(f"[topic_extraction] Model loaded on {'CUDA' if has_cuda else 'CPU'}")
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
