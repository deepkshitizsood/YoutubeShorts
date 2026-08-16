"""Pexels stock video lookup.

Real motion footage is the cheapest available retention upgrade: Pexels is free
for commercial use with no attribution, so a shot served from stock costs $0
instead of ~$0.04 for an AI still, and moves instead of sitting under a Ken
Burns pan.

Entirely optional - with no PEXELS_API_KEY set, every lookup returns None and
the caller falls back to AI images, so the pipeline still runs unchanged.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

from .http_util import raise_for_retryable_status, retry_call

# Pexels serves video search from the un-versioned host; some docs pages show a
# /v1 prefix, so both are tried before giving up.
SEARCH_ENDPOINTS = (
    "https://api.pexels.com/videos/search",
    "https://api.pexels.com/v1/videos/search",
)

# Below this the footage looks soft once cropped to 1080x1920.
MIN_HEIGHT = 960


def _api_key() -> str | None:
    return os.environ.get("PEXELS_API_KEY") or None


def _search(api_key: str, query: str, per_page: int = 8) -> list[dict]:
    params = {"query": query, "orientation": "portrait", "size": "medium", "per_page": per_page}
    headers = {"Authorization": api_key}
    last_error: Exception | None = None

    for endpoint in SEARCH_ENDPOINTS:
        def _call(url: str = endpoint) -> dict:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 404:
                raise FileNotFoundError(url)  # wrong host variant, try the next
            raise_for_retryable_status(resp, "Pexels video search")
            return resp.json()

        try:
            return retry_call(_call, description=f"Pexels search {query!r}").get("videos", [])
        except FileNotFoundError as e:
            last_error = e
            continue

    raise RuntimeError(f"No working Pexels video endpoint (last tried: {last_error})")


def _best_file(video: dict) -> dict | None:
    """Picks the smallest vertical file that still clears MIN_HEIGHT.

    Oversized 4K downloads waste runner time and bandwidth for a frame that gets
    cropped to 1080x1920 anyway, so the smallest acceptable file wins.
    """
    candidates = [
        f for f in video.get("video_files", [])
        if f.get("file_type") == "video/mp4"
        and f.get("height", 0) >= MIN_HEIGHT
        and f.get("height", 0) >= f.get("width", 0)  # vertical or square only
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda f: f.get("height", 0))


def fetch_clip(query: str, out_path: Path, min_duration: float = 2.0) -> Path | None:
    """Downloads a portrait stock clip for `query`. Returns None if unavailable.

    Never raises for the "no suitable footage" case - stock is a best-effort
    upgrade and the caller must be able to fall back to an AI image.
    """
    api_key = _api_key()
    if not api_key:
        return None

    try:
        videos = _search(api_key, query)
    except Exception as e:
        print(f"[stock] Search failed for {query!r} ({e}); falling back to AI image.", file=sys.stderr)
        return None

    for video in videos:
        if video.get("duration", 0) < min_duration:
            continue
        file_info = _best_file(video)
        if not file_info:
            continue
        try:
            resp = requests.get(file_info["link"], timeout=90)
            raise_for_retryable_status(resp, "Pexels clip download")
            out_path.write_bytes(resp.content)
            return out_path
        except Exception as e:
            print(f"[stock] Download failed for {query!r} ({e}); trying next result.", file=sys.stderr)
            continue

    return None
