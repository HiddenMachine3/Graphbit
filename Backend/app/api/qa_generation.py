"""Question-answer pair generation endpoint backed by Hugging Face Space API."""

import asyncio
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


async def _extract_gradio_queue_data(
    client: httpx.AsyncClient,
    call_url: str,
    event_id: str,
) -> object:
    def _extract_output(payload: object) -> object | None:
        if payload is None:
            return None

        if isinstance(payload, list) and payload:
            return payload[0]

        if isinstance(payload, dict):
            direct_data = payload.get("data")
            if isinstance(direct_data, list) and direct_data:
                return direct_data[0]

            output = payload.get("output")
            if isinstance(output, dict):
                nested_data = output.get("data")
                if isinstance(nested_data, list) and nested_data:
                    return nested_data[0]

        return None

    stream_url = f"{call_url.rstrip('/')}/{event_id}"
    last_payload_sample: str | None = None

    for attempt in range(6):
        collected_payloads: list[object] = []

        async with client.stream("GET", stream_url) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                raw_data = line[len("data:") :].strip()
                if not raw_data:
                    continue
                try:
                    payload = json.loads(raw_data)
                except json.JSONDecodeError:
                    continue

                extracted = _extract_output(payload)
                if extracted is not None:
                    return extracted

                collected_payloads.append(payload)

        for payload in reversed(collected_payloads):
            extracted = _extract_output(payload)
            if extracted is not None:
                return extracted

        if collected_payloads:
            last_payload_sample = json.dumps(collected_payloads[-1])[:240]

        if attempt < 5:
            await asyncio.sleep(1.0)

    detail = "Failed to read queued Hugging Face response"
    if last_payload_sample:
        detail = f"{detail}. Last payload: {last_payload_sample}"
    raise HTTPException(status_code=502, detail=detail)


def _coerce_qa_output(raw_payload: object) -> QAGenerationResponse:
    payload = raw_payload

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail="Hugging Face endpoint returned non-JSON qa payload",
            ) from exc

    if isinstance(payload, list):
        return QAGenerationResponse.model_validate({"qa_pairs": payload})

    if isinstance(payload, dict):
        return QAGenerationResponse.model_validate(payload)

    raise HTTPException(
        status_code=502,
        detail="Unexpected Hugging Face response format",
    )


@router.post("/qa/generate", response_model=QAGenerationResponse)
async def generate_qa_pairs(request: QAGenerationRequest) -> QAGenerationResponse:
    """Generate QA pairs by forwarding text and n to a Hugging Face Space Gradio endpoint."""
    payload = {
        "data": [
            request.text,
            request.n,
        ]
    }

    headers = {"Content-Type": "application/json"}
    if settings.HF_TOKEN:
        headers["Authorization"] = f"Bearer {settings.HF_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                settings.HF_QA_SPACE_API_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()

            if not isinstance(body, dict):
                raise HTTPException(status_code=502, detail="Invalid response from Hugging Face endpoint")

            if "event_id" in body and isinstance(body["event_id"], str):
                queued_output = await _extract_gradio_queue_data(
                    client=client,
                    call_url=settings.HF_QA_SPACE_API_URL,
                    event_id=body["event_id"],
                )
                return _coerce_qa_output(queued_output)

            raw_data = body.get("data")
            if not isinstance(raw_data, list) or not raw_data:
                raise HTTPException(status_code=502, detail="Missing data payload in Hugging Face response")

            return _coerce_qa_output(raw_data[0])
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to call Hugging Face QA endpoint: {exc}",
        ) from exc