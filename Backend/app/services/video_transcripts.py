"""Video transcript retrieval helpers."""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qs, urlparse


def fetch_youtube_transcript(video_url: str) -> str:
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        raise ValueError("Unable to parse YouTube video ID from URL")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise RuntimeError(
            "youtube-transcript-api is not installed. "
            "Install it or provide transcript text in the request."
        ) from exc

    transcript = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join(chunk.get("text", "") for chunk in transcript).strip()


def extract_youtube_video_id(video_url: str) -> Optional[str]:
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "youtu.be" in host:
        return path.split("/")[0] if path else None

    if "youtube" in host:
        if path.startswith("watch"):
            query = parse_qs(parsed.query)
            return query.get("v", [None])[0]
        if path.startswith("shorts/"):
            return path.split("/")[1] if "/" in path else None
        if path.startswith("embed/"):
            return path.split("/")[1] if "/" in path else None

    return None
