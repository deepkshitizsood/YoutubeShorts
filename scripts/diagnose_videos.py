"""Diagnostic: why did some videos get ~1 view while a sibling got 1,200+?

Pulls per-video reach metrics and traffic sources so the answer separates into
one of three cases:
  - impressions ~0        -> YouTube never surfaced it (distribution problem)
  - impressions high, CTR low -> viewers saw it and scrolled past (hook problem)
  - views ok, retention low   -> they clicked and left (content problem)

Read-only. Usage:  python -m scripts.diagnose_videos
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from src.analytics import recent_video_ids
from src.upload import credentials

# Reach metrics live in a different Analytics report than the engagement metrics
# the daily pipeline pulls, so they need their own query.
REACH_METRICS = "views,impressions,impressionClickThroughRate,averageViewPercentage"


def _analytics():
    return build("youtubeAnalytics", "v2", credentials=credentials())


def _query(**kwargs) -> dict:
    return _analytics().reports().query(ids="channel==MINE", **kwargs).execute()


def _rows(report: dict) -> list[dict]:
    cols = [h["name"] for h in report.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in report.get("rows", [])]


def main() -> None:
    videos = recent_video_ids(max_results=25)
    if not videos:
        print("No uploads found.")
        return

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=120)
    ids = [v["video_id"] for v in videos]

    print("=== REACH PER VIDEO ===")
    try:
        rows = _rows(_query(
            startDate=start.isoformat(), endDate=end.isoformat(),
            metrics=REACH_METRICS, dimensions="video",
            filters=f"video=={','.join(ids)}",
        ))
    except Exception as e:
        print(f"Reach query failed ({e}); impressions may not be exposed for Shorts.")
        rows = []

    for r in sorted(rows, key=lambda r: -r.get("views", 0)):
        print(
            f"  {r['video']}  views={r.get('views', 0):>6}  "
            f"impressions={r.get('impressions', 0):>7}  "
            f"CTR={r.get('impressionClickThroughRate', 0):>5.1f}%  "
            f"retention={r.get('averageViewPercentage', 0):>5.1f}%"
        )

    print()
    print("=== TRAFFIC SOURCES (whole channel) ===")
    try:
        for r in _rows(_query(
            startDate=start.isoformat(), endDate=end.isoformat(),
            metrics="views", dimensions="insightTrafficSourceType", sort="-views",
        )):
            print(f"  {r['insightTrafficSourceType']:<28} {r.get('views', 0)}")
    except Exception as e:
        print(f"Traffic-source query failed: {e}")

    print()
    print("=== PER-VIDEO TRAFFIC SOURCE (low performers) ===")
    weak = [r["video"] for r in rows if r.get("views", 0) < 50] or ids[:3]
    for vid in weak:
        print(f"  {vid}:")
        try:
            src = _rows(_query(
                startDate=start.isoformat(), endDate=end.isoformat(),
                metrics="views", dimensions="insightTrafficSourceType",
                filters=f"video=={vid}", sort="-views",
            ))
            if not src:
                print("    no traffic recorded at all - never surfaced")
            for r in src:
                print(f"    {r['insightTrafficSourceType']:<26} {r.get('views', 0)}")
        except Exception as e:
            print(f"    query failed: {e}")


if __name__ == "__main__":
    main()
