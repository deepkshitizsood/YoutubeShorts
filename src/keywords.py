"""Keyword reconnaissance against YouTube search.

Titles were previously invented blind - the prompt asked only for "curiosity-driven,
<=60 chars", with no requirement that the title contain anything a viewer might
actually type. Shorts that aren't attached to a searchable topic get no life beyond
the feed, which is one reason reach flat-lined at ~900 views per video.

This pulls the titles already ranking for a topic so the script step can write
against real demand instead of guessing.

Quota: search.list costs 100 units against the 10,000/day Data API budget, versus
1,600 for each videos.insert. At 3 posts/day that is ~5,100 units total - roughly
half the budget, with headroom. Failure is always non-fatal: recon is an
improvement, never a dependency.
"""
from __future__ import annotations

import sys

from googleapiclient.discovery import build

from .upload import credentials

MAX_RESULTS = 10


def _client():
    return build("youtube", "v3", credentials=credentials())


def competing_titles(query: str, max_results: int = MAX_RESULTS) -> list[str]:
    """Returns titles of Shorts already ranking for `query`, best-effort.

    Returns [] rather than raising: a quota error or outage should cost us the
    SEO edge for one video, not the video itself.
    """
    try:
        resp = _client().search().list(
            part="snippet",
            q=query,
            type="video",
            videoDuration="short",   # <4 min; the closest filter to Shorts
            order="relevance",
            maxResults=max_results,
        ).execute()
    except Exception as e:
        print(f"[keywords] Search recon failed for {query!r} ({e}); continuing without it.",
              file=sys.stderr)
        return []

    titles = []
    for item in resp.get("items", []):
        title = (item.get("snippet") or {}).get("title", "").strip()
        if title:
            titles.append(title)
    return titles


def recon_block(query: str) -> str:
    """Formats competing titles for injection into the script prompt."""
    titles = competing_titles(query)
    if not titles:
        return "(no search data available - write the best keyword-led title you can)"
    lines = "\n".join(f"  - {t}" for t in titles)
    return (
        f"Titles currently ranking on YouTube for '{query}':\n{lines}\n"
        "Use these to see the words real viewers search for on this subject. Match "
        "that vocabulary in your title, then beat them on specificity and curiosity - "
        "do NOT copy any of them."
    )


def normalize_tags(tags: list[str], max_total_chars: int = 460) -> list[str]:
    """Dedupes and clamps tags to stay inside YouTube's 500-char total budget.

    The prompt asks for 8-12 tags with no rule about duplication or length, and
    they were previously passed to the API verbatim. YouTube rejects the whole
    insert if the combined tag length exceeds its limit, so this trims rather
    than risking a failed upload. 460 leaves margin for separator overhead.
    """
    seen: set[str] = set()
    out: list[str] = []
    used = 0
    for raw in tags or []:
        tag = " ".join(str(raw).split()).strip().lower()
        if not tag or tag in seen or len(tag) > 60:
            continue
        cost = len(tag) + 1
        if used + cost > max_total_chars:
            break
        seen.add(tag)
        out.append(tag)
        used += cost
    return out
