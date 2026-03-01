"""Question-answer pair generation endpoint backed by Gemini API."""

import json
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter()


class QAGenerationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    n: int = Field(..., ge=1)
    question_type: Literal["open", "mcq", "flashcard"] = "open"


class OpenQAPair(BaseModel):
    question_type: Literal["open"] = "open"
    question: str
    answer: str


class MCQQAPair(BaseModel):
    question_type: Literal["mcq"] = "mcq"
    question: str
    options: list[str] = Field(..., min_length=2)
    answer: str


class FlashcardQAPair(BaseModel):
    question_type: Literal["flashcard"] = "flashcard"
    question: str
    answer: str


class OpenQAGenerationResponse(BaseModel):
    question_type: Literal["open"] = "open"
    qa_pairs: list[OpenQAPair]


class MCQQAGenerationResponse(BaseModel):
    question_type: Literal["mcq"] = "mcq"
    qa_pairs: list[MCQQAPair]


class FlashcardQAGenerationResponse(BaseModel):
    question_type: Literal["flashcard"] = "flashcard"
    qa_pairs: list[FlashcardQAPair]


def _normalize_question_type(
    value: object,
    default_type: Literal["open", "mcq", "flashcard"],
) -> Literal["open", "mcq", "flashcard"]:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"open", "mcq", "flashcard"}:
            return lowered
    return default_type


def _coerce_qa_output(
    raw_payload: object,
    question_type: Literal["open", "mcq", "flashcard"],
) -> OpenQAGenerationResponse | MCQQAGenerationResponse | FlashcardQAGenerationResponse:
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
        pairs = payload
        for pair in pairs:
            if isinstance(pair, dict):
                pair["question_type"] = _normalize_question_type(
                    pair.get("question_type"),
                    question_type,
                )
        if question_type == "mcq":
            return MCQQAGenerationResponse.model_validate(
                {"question_type": "mcq", "qa_pairs": pairs}
            )
        if question_type == "flashcard":
            return FlashcardQAGenerationResponse.model_validate(
                {"question_type": "flashcard", "qa_pairs": pairs}
            )
        return OpenQAGenerationResponse.model_validate(
            {"question_type": "open", "qa_pairs": pairs}
        )

    if isinstance(payload, dict):
        if isinstance(payload.get("qa_pairs"), list):
            for pair in payload["qa_pairs"]:
                if isinstance(pair, dict):
                    pair["question_type"] = _normalize_question_type(
                        pair.get("question_type"),
                        question_type,
                    )
        payload["question_type"] = _normalize_question_type(
            payload.get("question_type"),
            question_type,
        )
        if question_type == "mcq":
            return MCQQAGenerationResponse.model_validate(payload)
        if question_type == "flashcard":
            return FlashcardQAGenerationResponse.model_validate(payload)
        return OpenQAGenerationResponse.model_validate(payload)

    raise HTTPException(
        status_code=502,
        detail="Unexpected Gemini response format",
    )


@router.post(
    "/qa/generate",
    response_model=OpenQAGenerationResponse | MCQQAGenerationResponse | FlashcardQAGenerationResponse,
)
async def generate_qa_pairs(
    request: QAGenerationRequest,
) -> OpenQAGenerationResponse | MCQQAGenerationResponse | FlashcardQAGenerationResponse:
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

    if request.question_type == "mcq":
        schema = {
            "type": "object",
            "properties": {
                "question_type": {"type": "string", "enum": ["mcq"]},
                "qa_pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_type": {"type": "string", "enum": ["mcq"]},
                            "question": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 2,
                            },
                            "answer": {"type": "string"},
                        },
                        "required": ["question_type", "question", "options", "answer"],
                    },
                    "minItems": 1,
                },
            },
            "required": ["question_type", "qa_pairs"],
        }
        instruction = (
            "Generate exactly "
            f"{request.n} multiple-choice study question-answer pairs from the text below. "
            "Each pair must have question_type='mcq', a clear question, 4 concise options, and an answer "
            "that exactly matches one of the options. Avoid duplicate questions."
        )
    elif request.question_type == "flashcard":
        schema = {
            "type": "object",
            "properties": {
                "question_type": {"type": "string", "enum": ["flashcard"]},
                "qa_pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_type": {"type": "string", "enum": ["flashcard"]},
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                        },
                        "required": ["question_type", "question", "answer"],
                    },
                    "minItems": 1,
                },
            },
            "required": ["question_type", "qa_pairs"],
        }
        instruction = (
            "Generate exactly "
            f"{request.n} flashcard study question-answer pairs from the text below. "
            "Each pair must have question_type='flashcard'. Use short, direct prompt-answer style and avoid duplicates."
        )
    else:
        schema = {
            "type": "object",
            "properties": {
                "question_type": {"type": "string", "enum": ["open"]},
                "qa_pairs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_type": {"type": "string", "enum": ["open"]},
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                        },
                        "required": ["question_type", "question", "answer"],
                    },
                    "minItems": 1,
                },
            },
            "required": ["question_type", "qa_pairs"],
        }
        instruction = (
            "Generate exactly "
            f"{request.n} concise open-ended study question-answer pairs from the text below. "
            "Each pair must have question_type='open'. Use factual, direct wording and avoid duplicates."
        )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"Question type: {request.question_type}\n"
                            "Return JSON that strictly follows the response schema.\n\n"
                            f"{instruction}\n\n"
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

            return _coerce_qa_output(raw_json, request.question_type)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to call Gemini QA endpoint: {exc}",
        ) from exc