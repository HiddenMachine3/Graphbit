"""Video transcript retrieval helpers."""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import parse_qs, urlparse


def _fix_ssl_env() -> None:
    """Work around PostgreSQL installer overriding CA bundle env vars.

    PostgreSQL 18 on Windows sets CURL_CA_BUNDLE to a path that may not
    exist, and the ``requests`` library (used internally by
    youtube-transcript-api) picks it up — causing an OSError.  We swap
    it out for the bundle shipped with ``certifi`` if available.
    """
    for var in ("CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
        path = os.environ.get(var, "")
        if path and not os.path.isfile(path):
            try:
                import certifi
                os.environ[var] = certifi.where()
            except ImportError:
                os.environ.pop(var, None)


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

    _fix_ssl_env()

    # v1.x API: instantiate, then call .fetch() which returns a
    # FetchedTranscript with .snippets (list of snippet objects).
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id)
    return " ".join(s.text for s in fetched.snippets if s.text).strip()


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
