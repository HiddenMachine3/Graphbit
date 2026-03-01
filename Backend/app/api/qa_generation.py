"""Question-answer pair generation endpoint backed by Gemini API."""

import json

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter()


class QAGenerationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    n: int = Field(..., ge=1)


class QAPair(BaseModel):
    question: str
    answer: str


class QAGenerationResponse(BaseModel):
    qa_pairs: list[QAPair]


def _coerce_qa_output(raw_payload: object) -> QAGenerationResponse:
    payload = raw_payload

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="Gemini returned non-JSON QA payload",
            ) from exc

    if isinstance(payload, list):
        return QAGenerationResponse.model_validate({"qa_pairs": payload})

    if isinstance(payload, dict):
        return QAGenerationResponse.model_validate(payload)

    raise HTTPException(
        status_code=502,
        detail="Unexpected Gemini response format",
    )


@router.post("/qa/generate", response_model=QAGenerationResponse)
async def generate_qa_pairs(request: QAGenerationRequest) -> QAGenerationResponse:
    """Generate QA pairs using Gemini API with structured JSON output."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured",
        )

    model = settings.GEMINI_QA_MODEL
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    schema = {
        "type": "object",
        "properties": {
            "qa_pairs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                    },
                    "required": ["question", "answer"],
                },
                "minItems": 1,
            }
        },
        "required": ["qa_pairs"],
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Generate exactly "
                            f"{request.n} concise study question-answer pairs from the text below. "
                            "Use factual, direct wording and avoid duplicate questions.\n\n"
                            f"Text:\n{request.text}"
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "response_mime_type": "application/json",
            "response_schema": schema,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            body = response.json()

            if not isinstance(body, dict):
                raise HTTPException(status_code=502, detail="Invalid response from Gemini")

            try:
                raw_json = body["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as exc:
                raise HTTPException(
                    status_code=502,
                    detail="Gemini response missing candidates content",
                ) from exc

            return _coerce_qa_output(raw_json)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to call Gemini QA endpoint: {exc}",
        ) from exc