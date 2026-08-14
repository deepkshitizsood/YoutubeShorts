"""Pulls recent Shorts performance from the YouTube Analytics API and appends
it to data/performance_log.json - the raw material the strategy step reads to
decide what to make more (or less) of."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from . import config as cfg
from .upload import credentials

LOOKBACK_DAYS = 14


def _analytics_client():
    return build("youtubeAnalytics", "v2", credentials=credentials())


def _data_client():
    return build("youtube", "v3", credentials=credentials())


def recent_video_ids(max_results: int = 20) -> list[dict]:
    """Returns [{video_id, published_at}] for the channel's most recent uploads."""
    youtube = _data_client()
    channels = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_playlist = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items = youtube.playlistItems().list(
        part="snippet", playlistId=uploads_playlist, maxResults=max_results
    ).execute()

    return [
        {
            "video_id": it["snippet"]["resourceId"]["videoId"],
            "published_at": it["snippet"]["publishedAt"],
        }
        for it in items.get("items", [])
    ]


def fetch_stats(video_ids: list[str], start_date: str, end_date: str) -> dict[str, dict]:
    if not video_ids:
        return {}
    analytics = _analytics_client()
    report = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views,likes,comments,shares,averageViewDuration,averageViewPercentage",
        dimensions="video",
        filters=f"video=={','.join(video_ids)}",
    ).execute()

    columns = [h["name"] for h in report.get("columnHeaders", [])]
    stats = {}
    for row in report.get("rows", []):
        record = dict(zip(columns, row))
        stats[record["video"]] = record
    return stats


def pull_and_log() -> list[dict]:
    """Fetches stats for recent uploads and appends fresh entries to performance_log.json.
    Returns the newly appended entries."""
    videos = recent_video_ids()
    if not videos:
        return []

    end_date = datetime.now(timezone.utc).date().isoformat()
    start_date = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    video_ids = [v["video_id"] for v in videos]
    stats = fetch_stats(video_ids, start_date, end_date)

    with open(cfg.PERFORMANCE_LOG_PATH, "r", encoding="utf-8") as f:
        log = json.load(f)

    now = datetime.now(timezone.utc)
    new_entries = []
    for v in videos:
        s = stats.get(v["video_id"])
        if not s:
            continue
        published = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        hours_since_publish = max((now - published).total_seconds() / 3600.0, 1.0)
        entry = {
            "video_id": v["video_id"],
            "pulled_at": now.isoformat(),
            "hours_since_publish": round(hours_since_publish, 1),
            "views": int(s.get("views", 0)),
            "likes": int(s.get("likes", 0)),
            "comments": int(s.get("comments", 0)),
            "shares": int(s.get("shares", 0)),
            "average_view_duration_seconds": float(s.get("averageViewDuration", 0)),
            "average_view_percentage": float(s.get("averageViewPercentage", 0)),
        }
        log.append(entry)
        new_entries.append(entry)

    with open(cfg.PERFORMANCE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    return new_entries
