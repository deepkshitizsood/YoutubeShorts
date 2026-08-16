"""Picks today's content pillar and topic angle from past performance.

Simple exploit/explore weighting (not a full multi-armed bandit, deliberately -
with ~1 data point/day there isn't enough signal to justify more complexity):
  - Score each pillar by avg views-per-hour-since-publish of its recent videos.
  - 80% of the time, pick the best-scoring pillar (exploit).
  - 20% of the time, pick a random other pillar (explore), so the channel
    doesn't calcify around one early lucky topic before enough data exists.
"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone

from . import config as cfg


def load_performance_log() -> list[dict]:
    with open(cfg.PERFORMANCE_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_content_history() -> list[dict]:
    with open(cfg.CONTENT_HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def append_content_history(entry: dict) -> None:
    history = load_content_history()
    history.append(entry)
    with open(cfg.CONTENT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def score_video(entry: dict) -> float:
    """Scores a single video, weighted toward what actually drives Shorts reach.

    Retention is the dominant term: YouTube gates wider distribution on
    watch-through, and a high-retention video with few views is a better bet to
    repeat than a high-view video people swipe away from. Views-per-hour is kept
    as a secondary velocity term, and engagement as a small tiebreaker. All of
    this data was already being collected and thrown away.
    """
    retention = entry.get("average_view_percentage", 0.0) / 100.0  # 0..1
    hours_live = max(entry.get("hours_since_publish", 1.0), 1.0)
    views = entry.get("views", 0)
    views_per_hour = views / hours_live

    engagement = entry.get("likes", 0) + 2 * entry.get("comments", 0) + 3 * entry.get("shares", 0)
    engagement_rate = engagement / max(views, 1)

    # log1p keeps a single breakout video from permanently pinning the channel
    # to one pillar before there is enough evidence.
    return (
        3.0 * retention
        + 1.0 * math.log1p(views_per_hour)
        + 2.0 * engagement_rate
    )


def _videos_for_pillar(pillar_id: str, history: list[dict]) -> set[str]:
    return {
        h["video_id"] for h in history
        if h.get("pillar_id") == pillar_id and h.get("video_id") and not h.get("dry_run")
    }


def _score_pillar(pillar_id: str, log: list[dict], history: list[dict]) -> float | None:
    """Mean score across that pillar's videos - one sample per video."""
    video_ids = _videos_for_pillar(pillar_id, history)
    if not video_ids:
        return None
    scores = [score_video(e) for e in log if e.get("video_id") in video_ids]
    if not scores:
        return None
    return sum(scores) / len(scores)


def length_variant_report(log: list[dict], history: list[dict]) -> dict[str, dict]:
    """Mean score per length variant, to settle the 30s-vs-50s question with data."""
    by_video = {e["video_id"]: e for e in log if e.get("video_id")}
    buckets: dict[str, list[float]] = {}
    for h in history:
        variant, vid = h.get("length_variant"), h.get("video_id")
        if not variant or not vid or h.get("dry_run") or vid not in by_video:
            continue
        buckets.setdefault(variant, []).append(score_video(by_video[vid]))
    return {
        name: {"videos": len(s), "mean_score": round(sum(s) / len(s), 3)}
        for name, s in buckets.items() if s
    }


EXPLORE_PROBABILITY = 0.25


def pick_pillar(config: dict, log: list[dict], history: list[dict]) -> tuple[dict, bool]:
    """Returns (pillar_config, is_exploration)."""
    pillars = config["content"]["pillars"]
    scored = [(p, _score_pillar(p["id"], log, history)) for p in pillars]
    known = [(p, s) for p, s in scored if s is not None]

    # Not enough data yet (early days) - fall back to configured static weights.
    if len(known) < 2:
        weights = [p["weight"] for p in pillars]
        return random.choices(pillars, weights=weights, k=1)[0], False

    best_pillar, _ = max(known, key=lambda ps: ps[1])

    # Any pillar with no data at all is worth trying before exploiting further -
    # otherwise an untried pillar can only ever be reached by chance.
    untried = [p for p, s in scored if s is None]
    if untried:
        return random.choice(untried), True

    if random.random() < EXPLORE_PROBABILITY:
        # Explore means "something other than the current best". Choosing
        # uniformly over all pillars re-picked the best ~1/3 of the time and
        # labelled those runs as exploration anyway.
        alternatives = [p for p in pillars if p["id"] != best_pillar["id"]]
        if alternatives:
            return random.choice(alternatives), True

    return best_pillar, False


def recent_topics(history: list[dict], limit: int = 60) -> list[str]:
    """Topics to show the LLM as 'already covered'.

    The window is sized in videos, not days, so it has to scale with posting
    cadence: at 3/day a 20-item window covers under a week.
    """
    return [h["topic"] for h in history[-limit:] if h.get("topic")]


def used_topics() -> set[str]:
    """Every topic ever produced, for the hard uniqueness check.

    Includes dry runs deliberately - a topic rehearsed in a dry run has usually
    been reviewed already, and regenerating is cheap next to publishing a
    near-duplicate.
    """
    return {h["topic"].strip().lower() for h in load_content_history() if h.get("topic")}


def print_learning_report() -> None:
    """Prints what the loop currently believes, so each run log shows its reasoning."""
    log = load_performance_log()
    history = load_content_history()
    if not log:
        print("[learn] No analytics yet (YouTube lags ~72h) - using configured weights.")
        return

    config = cfg.load_config()
    ranked = sorted(
        (
            (p["id"], _score_pillar(p["id"], log, history))
            for p in config["content"]["pillars"]
        ),
        key=lambda kv: (kv[1] is not None, kv[1]),
        reverse=True,
    )
    summary = ", ".join(
        f"{pid}={score:.2f}" if score is not None else f"{pid}=no-data" for pid, score in ranked
    )
    print(f"[learn] Pillar scores from {len(log)} video(s): {summary}")

    lengths = length_variant_report(log, history)
    if lengths:
        detail = ", ".join(
            f"{name}={v['mean_score']} (n={v['videos']})" for name, v in lengths.items()
        )
        print(f"[learn] Length variants: {detail}")

    best = max(log, key=score_video)
    print(
        f"[learn] Best video so far: {best['video_id']} "
        f"({best.get('views', 0)} views, {best.get('average_view_percentage', 0):.0f}% retention)"
    )


def build_strategy_brief(config: dict) -> dict:
    log = load_performance_log()
    history = load_content_history()
    pillar, is_exploration = pick_pillar(config, log, history)
    return {
        "pillar_id": pillar["id"],
        "pillar_description": pillar["description"],
        "is_exploration": is_exploration,
        "recent_topics_to_avoid": recent_topics(history),
        "picked_at": datetime.now(timezone.utc).isoformat(),
    }
