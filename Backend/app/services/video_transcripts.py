"""YouTube transcript service helpers."""

from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse


def extract_youtube_video_id(video_url: str) -> str | None:
    parsed = urlparse((video_url or "").strip())
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")

    if host in {"youtu.be", "www.youtu.be"} and path:
        return path.split("/")[0]

    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if path == "watch":
            query = parse_qs(parsed.query)
            values = query.get("v")
            if values and values[0]:
                return values[0]
        if path.startswith("shorts/"):
            return path.split("/", 1)[1].split("/")[0]
        if path.startswith("embed/"):
            return path.split("/", 1)[1].split("/")[0]

    return None


def looks_like_single_url(value: str) -> bool:
    text = (value or "").strip()
    if not text or " " in text or "\n" in text:
        return False
    parsed = urlparse(text)
    return bool(parsed.scheme and parsed.netloc)


def transcript_to_text(segments: list[dict] | list[object]) -> str:
    lines = []
    for segment in segments:
        if isinstance(segment, dict):
            raw_text = segment.get("text")
        else:
            raw_text = getattr(segment, "text", None)
        value = (raw_text or "").strip()
        if value:
            lines.append(value)
    return "\n\n".join(lines).strip()


def _to_raw_segments(value: object) -> list[dict] | list[object]:
    if hasattr(value, "to_raw_data"):
        return value.to_raw_data()
    return value


def _build_proxy_config():
    try:
        from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig
    except Exception:
        return None

    webshare_username = (os.environ.get("YOUTUBE_WEBSHARE_PROXY_USERNAME") or "").strip()
    webshare_password = (os.environ.get("YOUTUBE_WEBSHARE_PROXY_PASSWORD") or "").strip()
    if webshare_username and webshare_password:
        locations_raw = (os.environ.get("YOUTUBE_WEBSHARE_FILTER_IP_LOCATIONS") or "").strip()
        locations = [part.strip() for part in locations_raw.split(",") if part.strip()] if locations_raw else None
        return WebshareProxyConfig(
            proxy_username=webshare_username,
            proxy_password=webshare_password,
            filter_ip_locations=locations,
        )

    http_url = (os.environ.get("YOUTUBE_PROXY_HTTP_URL") or "").strip()
    https_url = (os.environ.get("YOUTUBE_PROXY_HTTPS_URL") or "").strip()
    if http_url or https_url:
        return GenericProxyConfig(
            http_url=http_url or None,
            https_url=https_url or None,
        )

    return None


def _create_api_client():
    from youtube_transcript_api import YouTubeTranscriptApi

    proxy_config = _build_proxy_config()
    if proxy_config is not None:
        return YouTubeTranscriptApi(proxy_config=proxy_config)
    return YouTubeTranscriptApi()


def fetch_youtube_transcript_segments(
    video_url: str,
    languages: list[str] | None = None,
) -> tuple[list[dict] | list[object], str]:
    """Fetch transcript segments for a YouTube URL.

    Returns tuple of (segments, strategy_used).
    """
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        raise ValueError("Unable to parse YouTube video ID from URL")

    requested_languages = languages or ["en", "en-US", "en-GB"]

    from youtube_transcript_api import YouTubeTranscriptApi

    primary_error: Exception | None = None
    try:
        api_client = _create_api_client()
        if hasattr(api_client, "fetch"):
            fetched = api_client.fetch(video_id, languages=requested_languages)
            segments = _to_raw_segments(fetched)
            if segments and len(segments) > 0:
                return segments, "fetch"

        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            segments = YouTubeTranscriptApi.get_transcript(video_id)
            if segments and len(segments) > 0:
                return segments, "get_transcript"

        raise ValueError("Primary transcript methods returned empty data")
    except Exception as exc:
        primary_error = exc

    try:
        api_client = _create_api_client()
        if hasattr(api_client, "list"):
            transcript_list = api_client.list(video_id)
        elif hasattr(YouTubeTranscriptApi, "list_transcripts"):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        else:
            raise RuntimeError("No transcript listing method available")

        fetched_transcript = None
        try:
            fetched_transcript = transcript_list.find_transcript(requested_languages)
        except Exception:
            pass

        if fetched_transcript is None:
            for candidate in transcript_list:
                fetched_transcript = candidate
                break

        if fetched_transcript is None:
            raise ValueError("No transcript entries available")

        fetched = fetched_transcript.fetch()
        segments = _to_raw_segments(fetched)
        if not segments or len(segments) == 0:
            raise ValueError("Fallback transcript fetch returned empty data")
        return segments, "list"
    except Exception as fallback_exc:
        primary_reason = f"{type(primary_error).__name__}: {primary_error}" if primary_error else "unknown"
        fallback_reason = f"{type(fallback_exc).__name__}: {fallback_exc}"
        raise RuntimeError(f"Primary: {primary_reason}. Fallback: {fallback_reason}") from fallback_exc


def fetch_youtube_transcript(video_url: str, languages: list[str] | None = None) -> tuple[str, str]:
    """Fetch transcript text for a YouTube URL.

    Returns tuple of (transcript_text, strategy_used).
    """
    segments, strategy_used = fetch_youtube_transcript_segments(video_url, languages=languages)
    return transcript_to_text(segments), strategy_used
