"""Pulls recent Shorts performance from the YouTube Analytics API and appends
it to data/performance_log.json - the raw material the strategy step reads to
decide what to make more (or less) of."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from . import config as cfg
from .upload import credentials

# Long enough to cover a video's whole life for scoring purposes.
LOOKBACK_DAYS = 120
# YouTube Analytics is documented as lagging up to ~72h; below this age, an
# empty result is normal rather than a symptom of something being broken.
ANALYTICS_LAG_HOURS = 72


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
    """Refreshes lifetime stats for recent uploads into performance_log.json.

    Stores exactly ONE row per video, overwritten in place on each run. The
    previous append-only behaviour accumulated a snapshot per video per day
    (~2.4MB/year, committed to git daily) and skewed scoring toward older videos,
    which simply had more snapshots to average over.

    Note YouTube Analytics lags by up to 72h, so a video published today will
    legitimately return nothing for a couple of days - that is reported rather
    than silently swallowed.
    """
    videos = recent_video_ids()
    if not videos:
        print("[analytics] No uploads found on the channel yet.")
        return []

    # startDate is deliberately far enough back to capture each video's whole
    # life: pairing a trailing window of views with a lifetime age made every
    # video's score decay toward zero purely from getting older.
    end_date = datetime.now(timezone.utc).date().isoformat()
    start_date = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    video_ids = [v["video_id"] for v in videos]
    stats = fetch_stats(video_ids, start_date, end_date)

    with open(cfg.PERFORMANCE_LOG_PATH, "r", encoding="utf-8") as f:
        log = json.load(f)
    by_id = {e["video_id"]: e for e in log if e.get("video_id")}

    now = datetime.now(timezone.utc)
    updated = []
    awaiting_data = []
    for v in videos:
        s = stats.get(v["video_id"])
        published = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        hours_since_publish = max((now - published).total_seconds() / 3600.0, 1.0)
        if not s:
            if hours_since_publish < ANALYTICS_LAG_HOURS:
                awaiting_data.append(v["video_id"])
            continue
        entry = {
            "video_id": v["video_id"],
            "published_at": v["published_at"],
            "pulled_at": now.isoformat(),
            "hours_since_publish": round(hours_since_publish, 1),
            "views": int(s.get("views", 0)),
            "likes": int(s.get("likes", 0)),
            "comments": int(s.get("comments", 0)),
            "shares": int(s.get("shares", 0)),
            "average_view_duration_seconds": float(s.get("averageViewDuration", 0)),
            "average_view_percentage": float(s.get("averageViewPercentage", 0)),
        }
        by_id[entry["video_id"]] = entry
        updated.append(entry)

    with open(cfg.PERFORMANCE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(by_id.values(), key=lambda e: e.get("published_at") or ""), f, indent=2)

    if awaiting_data:
        print(
            f"[analytics] {len(awaiting_data)} video(s) published within the last "
            f"{ANALYTICS_LAG_HOURS}h have no data yet (YouTube reporting lag) - expected."
        )
    stale = len(videos) - len(updated) - len(awaiting_data)
    if stale > 0:
        print(f"[analytics] {stale} older video(s) returned no rows - check API scope/quota.")

    return updated

    return new_entries
