"""Answer verification using Gemini API with keyword fallback."""

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def verify_answer_with_llm(
    user_answer: str,
    correct_answer: str,
    question_text: str,
    **kwargs,
) -> dict:
    """
    Verify an open-ended answer using Gemini, with keyword fallback.

    Returns:
        A dict with keys:
            - 'correct' (bool)
            - 'score' (float or None)
            - 'explanation' (str)
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set, falling back to keyword matching")
        return _keyword_matching(user_answer, correct_answer)

    try:
        return await _gemini_verify(api_key, user_answer, correct_answer, question_text)
    except Exception as exc:
        logger.warning("Gemini verification failed, falling back to keywords: %s", exc)
        return _keyword_matching(user_answer, correct_answer)


async def _gemini_verify(
    api_key: str,
    user_answer: str,
    correct_answer: str,
    question_text: str,
) -> dict:
    """Call Gemini to semantically evaluate the answer."""
    model = "gemini-2.0-flash"
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    prompt = (
        "You are a strict but fair exam grader. Evaluate whether the student's answer "
        "is semantically correct compared to the reference answer.\n\n"
        f"Question: {question_text}\n"
        f"Reference answer: {correct_answer}\n"
        f"Student answer: {user_answer}\n\n"
        "Return JSON with exactly these keys:\n"
        '- "correct": true/false (is the student answer substantially correct?)\n'
        '- "explanation": a short one-sentence explanation for the grading decision'
    )

    schema = {
        "type": "object",
        "properties": {
            "correct": {"type": "boolean"},
            "explanation": {"type": "string"},
        },
        "required": ["correct", "explanation"],
    }

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256,
            "response_mime_type": "application/json",
            "response_schema": schema,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        body = response.json()

    raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(raw_text)

    logger.info(
        "Gemini answer verification: correct=%s explanation=%s",
        result.get("correct"),
        (result.get("explanation") or "")[:80],
    )

    return {
        "correct": bool(result.get("correct", False)),
        "score": None,
        "explanation": result.get("explanation", ""),
    }


def _keyword_matching(user_answer: str, correct_answer: str) -> dict:
    """Keyword matching fallback for answer verification."""
    user_answer_lower = user_answer.strip().lower()
    correct_answer_lower = correct_answer.lower()

    key_words = [w for w in correct_answer_lower.split() if len(w) > 3]

    if not key_words:
        return {
            "correct": user_answer_lower == correct_answer_lower,
            "score": None,
            "explanation": f"Expected: {correct_answer}",
        }

    matches = sum(1 for word in key_words if word in user_answer_lower)
    match_ratio = matches / len(key_words)
    is_correct = match_ratio >= 0.5

    return {
        "correct": is_correct,
        "score": None,
        "explanation": (
            "Correct! Great understanding." if is_correct
            else f"Not quite. The answer should mention: {correct_answer}"
        ),
    }
