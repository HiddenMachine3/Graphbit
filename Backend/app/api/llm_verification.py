"""LLM-based answer verification using a Hugging Face reward model."""

from typing import Optional
import logging
import os
import asyncio

# async HTTP client
try:
    import httpx
except Exception:
    httpx = None  # we'll handle fallback

logger = logging.getLogger(__name__)

async def verify_answer_with_llm(
    user_answer: str,
    correct_answer: str,
    question_text: str,
    *,
    hf_token_env: str = "HF_TOKEN_REWARD",
    hf_model: str = "Skywork/Skywork-Reward-V2-Qwen3-8B",
    threshold: float = 0.0,
    explain_with_gen: bool = False,
    gen_model: Optional[str] = None,
) -> dict:
    """
    Verify an open-ended answer using a Hugging Face reward model.

    Args:
        user_answer: The answer provided by the user
        correct_answer: The expected/correct answer
        question_text: The question being answered
        hf_token_env: env var name that holds the Hugging Face token
        hf_model: Hugging Face model id for the reward model
        threshold: numeric threshold on the reward model score above which we mark correct
        explain_with_gen: if True, call an additional generative model to produce a human explanation
        gen_model: optional generative model id (if None, looks at HF_GEN_MODEL env var)

    Returns:
        A dict with keys:
            - 'correct' (bool)
            - 'score' (float or None)
            - 'explanation' (str)
    """

    hf_token = os.getenv(hf_token_env) or os.getenv("HF_API_TOKEN")
    if not hf_token:
        logger.warning("Reward model disabled: missing HF token env (%s or HF_API_TOKEN).", hf_token_env)
        return _keyword_matching(user_answer, correct_answer)
    if httpx is None:
        logger.warning("Reward model disabled: httpx not installed.")
        return _keyword_matching(user_answer, correct_answer)

    # Build the combined input the reward model expects
    payload_text = (
        f"QUESTION: {question_text}\n"
        f"EXPECTED: {correct_answer}\n"
        f"RESPONSE: {user_answer}"
    )

    api_url = f"https://api-inference.huggingface.co/models/{hf_model}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    try:
        logger.info("Calling HF reward model: %s", hf_model)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(api_url, headers=headers, json={"inputs": payload_text})
            resp.raise_for_status()
            data = resp.json()

        # Parse common HF RM response shapes. Examples:
        # [{"label": "LABEL_1", "score": 2.37}]  OR  [{"score": 2.37}]  OR {"error": "..."}
        score = None
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"Hugging Face inference error: {data['error']}")

        if isinstance(data, list) and len(data) > 0:
            first = data[0]
            if isinstance(first, dict):
                # prefer explicit 'score'
                if "score" in first and isinstance(first["score"], (int, float)):
                    score = float(first["score"])
                # sometimes models return logits in other keys; try to coerce any numeric value
                else:
                    # find first numeric value in dict
                    for v in first.values():
                        if isinstance(v, (int, float)):
                            score = float(v)
                            break

        if score is None:
            # As a last resort try to find any number in the top-level response (very unlikely)
            import re
            text = str(data)
            m = re.search(r"-?\d+(\.\d+)?", text)
            if m:
                score = float(m.group(0))

        # If still None, fallback to keyword matching
        if score is None:
            logger.warning("Reward model response had no score. Falling back to keyword matching.")
            return _keyword_matching(user_answer, correct_answer)

        is_correct = score >= threshold

        explanation = (
            f"Score: {score:.4f}. "
            + ("Marked correct (>= threshold)." if is_correct else f"Marked incorrect (< threshold {threshold}).")
        )

        # Optional: ask a generative model on HF for a short explanation (only if requested)
        if explain_with_gen:
            gen_id = gen_model or os.getenv("HF_GEN_MODEL")
            if gen_id:
                try:
                    logger.info("Calling HF generative model for explanation: %s", gen_id)
                    gen_expl = await _generate_explanation(
                        question_text, correct_answer, user_answer, gen_id, hf_token
                    )
                    # prefer the generative explanation but keep the score summary
                    explanation = f"{explanation}\n\nExplanation:\n{gen_expl.strip()}"
                except Exception as exc:
                    logger.warning("HF generative explanation failed: %s", exc)
                    pass

        return {"correct": bool(is_correct), "score": float(score), "explanation": explanation}

    except Exception as e:
        logger.warning("Reward model verification failed: %s; falling back to keyword matching.", e)
        return _keyword_matching(user_answer, correct_answer)


def _keyword_matching(user_answer: str, correct_answer: str) -> dict:
    """Fallback keyword matching for answer verification."""
    user_answer_lower = user_answer.strip().lower()
    correct_answer_lower = correct_answer.lower()

    # Extract key words (words longer than 3 characters)
    key_words = [w for w in correct_answer_lower.split() if len(w) > 3]

    if not key_words:
        return {
            "correct": user_answer_lower == correct_answer_lower,
            "score": None,
            "explanation": f"Expected: {correct_answer}",
        }

    # Count matches
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


async def _generate_explanation(question: str, expected: str, response: str, gen_model: str, hf_token: str) -> str:
    """
    Optional: call a generative HF model to produce a short explanation.
    This uses the HF text-generation inference endpoint and returns the generated text.
    """
    api_url = f"https://api-inference.huggingface.co/models/{gen_model}"
    headers = {"Authorization": f"Bearer {hf_token}"}

    prompt = (
        f"Question: {question}\n"
        f"Expected Answer: {expected}\n"
        f"Student's Answer: {response}\n\n"
        "Briefly explain why the student's answer is correct or incorrect relative to the expected answer. "
        "Be concise (1-2 short sentences)."
    )

    # Prefer httpx if available
    if httpx is None:
        raise RuntimeError("httpx library is required for generation.")

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(api_url, headers=headers, json={"inputs": prompt, "parameters": {"max_new_tokens": 120}})
        r.raise_for_status()
        out = r.json()

    # Parse common forms: [{"generated_text":"..."}] or {"error": "..."} or string
    if isinstance(out, list) and len(out) > 0 and isinstance(out[0], dict):
        # try common keys
        for key in ("generated_text", "summary_text", "text", "content"):
            if key in out[0]:
                return out[0][key]
        # else fallback to stringified first elem
        return str(out[0])
    elif isinstance(out, dict) and "error" in out:
        raise RuntimeError(out["error"])
    else:
        return str(out)


# Example usage (in async context):
# import asyncio
# res = asyncio.run(verify_answer_with_llm("Paris", "Paris", "What is the capital of France?"))
# print(res)
