"""LLM-based answer verification for open-ended questions."""

from typing import Optional
import os


async def verify_answer_with_llm(
    user_answer: str,
    correct_answer: str,
    question_text: str,
) -> dict:
    """
    Verify an open-ended answer using an LLM.
    
    Uses OpenAI's API if OPENAI_API_KEY is set, otherwise falls back to keyword matching.
    
    Args:
        user_answer: The answer provided by the user
        correct_answer: The expected/correct answer
        question_text: The question being answered
    
    Returns:
        A dict with 'correct' (bool) and 'explanation' (str)
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        # Fallback to keyword matching if no API key
        return _keyword_matching(user_answer, correct_answer)
    
    try:
        import openai
        openai.api_key = api_key
        
        prompt = f"""You are an expert educator grading student answers.

Question: {question_text}
Expected Answer: {correct_answer}
Student's Answer: {user_answer}

Evaluate if the student's answer demonstrates understanding of the concept. Consider:
- Does it capture the key idea?
- Is the explanation accurate?
- Would this answer be acceptable in an educational context?

Respond with JSON only (no markdown, no extra text):
{{"correct": true/false, "explanation": "brief feedback"}}"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            "correct": result.get("correct", False),
            "explanation": result.get("explanation", "Unable to verify answer."),
        }
    except Exception as e:
        # If LLM fails, fall back to keyword matching
        print(f"LLM verification failed: {e}, falling back to keyword matching")
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
            "explanation": f"Expected: {correct_answer}",
        }
    
    # Count matches
    matches = sum(1 for word in key_words if word in user_answer_lower)
    match_ratio = matches / len(key_words)
    
    is_correct = match_ratio >= 0.5
    
    return {
        "correct": is_correct,
        "explanation": (
            "Correct! Great understanding." if is_correct
            else f"Not quite. The answer should mention: {correct_answer}"
        ),
    }
