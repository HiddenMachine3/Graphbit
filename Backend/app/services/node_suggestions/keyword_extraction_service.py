from app.core.config import settings


class KeywordExtractionService:
    def __init__(self, client):
        self.client = client

    def extract_phrases(self, text: str) -> list[str]:
        if not text.strip():
            return []
        results = self.client.token_classification(
            text,
            model=getattr(settings, "HF_KEYPHRASE_MODEL", None),
        )
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
