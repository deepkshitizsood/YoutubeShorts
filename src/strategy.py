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


def _score_pillar(pillar_id: str, log: list[dict], history: list[dict]) -> float | None:
    video_ids_for_pillar = {
        h["video_id"] for h in history if h.get("pillar_id") == pillar_id and h.get("video_id")
    }
    if not video_ids_for_pillar:
        return None
    scores = []
    for entry in log:
        if entry.get("video_id") not in video_ids_for_pillar:
            continue
        views = entry.get("views", 0)
        hours_live = max(entry.get("hours_since_publish", 1), 1)
        scores.append(views / hours_live)
    if not scores:
        return None
    return sum(scores) / len(scores)


def pick_pillar(config: dict, log: list[dict], history: list[dict]) -> tuple[dict, bool]:
    """Returns (pillar_config, is_exploration)."""
    pillars = config["content"]["pillars"]
    scored = [(p, _score_pillar(p["id"], log, history)) for p in pillars]
    known = [(p, s) for p, s in scored if s is not None]

    # Not enough data yet (early days) - fall back to configured static weights.
    if len(known) < 2:
        weights = [p["weight"] for p in pillars]
        return random.choices(pillars, weights=weights, k=1)[0], False

    if random.random() < 0.2:
        return random.choice(pillars), True

    best_pillar, _ = max(known, key=lambda ps: ps[1])
    return best_pillar, False


def recent_topics(history: list[dict], limit: int = 20) -> list[str]:
    return [h["topic"] for h in history[-limit:] if h.get("topic")]


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
