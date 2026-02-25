import logging
import os

from app.core.config import settings


logger = logging.getLogger(__name__)


class KeywordExtractionService:
    def __init__(self, client):
        self.client = client

    def extract_phrases(self, text: str) -> list[str]:
        if not text.strip():
            return []
        model_name = getattr(settings, "HF_KEYPHRASE_MODEL", None)
        base_url = os.environ.get(
            "HF_INFERENCE_BASE_URL",
            "https://router.huggingface.co/hf-inference",
        ).rstrip("/")
        model_target = model_name
        if model_name and isinstance(model_name, str) and not model_name.startswith(("http://", "https://")):
            model_target = f"{base_url}/models/{model_name}"
        try:
            results = self.client.token_classification(
                text,
                model=model_target,
            )
        except Exception as exc:
            logger.exception(
                "Keyword extraction model call failed. model=%s target=%s",
                model_name,
                model_target,
            )
            raise RuntimeError(f"HF keyword extraction failed for model '{model_name}': {exc}") from exc

        phrases: list[str] = []
        current = ""
        for item in results or []:
            word = item.get("word", "")
            if not word:
                continue
            if word.startswith("##"):
                current += word.replace("##", "")
                continue
            if current:
                phrases.append(current)
            current = word
        if current:
            phrases.append(current)

        normalized = []
        seen = set()
        for phrase in phrases:
            cleaned = phrase.strip().lower()
            if len(cleaned) < 3 or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized
