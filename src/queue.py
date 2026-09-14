"""Owns data/script_queue.json - the pre-generated, pre-approved scripts
produced by src/gen_scripts.py, consumed by main.py when
content.script_source == "queue" (see config.yaml).

item_to_pipeline_data() is the single adapter seam: everything downstream of
script acquisition in main.py (TTS, visuals, assemble, upload, history) reads
the same dict shape regardless of whether script_gen.py or this queue
produced it, so none of that code needs to know which path is active.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import config as cfg


def load_queue() -> dict:
    with open(cfg.SCRIPT_QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: dict) -> None:
    with open(cfg.SCRIPT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)


def append_script_queue(items: list[dict]) -> None:
    queue = load_queue()
    queue["entries"].extend(items)
    save_queue(queue)


def pop_for_pillar(config: dict, pillar_id: str) -> dict | None:
    """FIFO within clusters that map onto `pillar_id`. Marks the item
    'popped' (not yet 'published') so a crash mid-upload doesn't lose track
    of which item was in flight - main.py finalizes it via mark_published()
    in the same finally block that already handles this for the live path."""
    cluster_map = config["content"]["ideation"]["cluster_pillar_map"]
    queue = load_queue()
    candidates = [
        e for e in queue["entries"]
        if e.get("status") == "queued" and cluster_map.get(e.get("cluster")) == pillar_id
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda e: e.get("queued_at", ""))
    chosen = candidates[0]
    chosen["status"] = "popped"
    save_queue(queue)
    return chosen


def pop_any_queued(config: dict) -> dict | None:
    """Fallback when no queued item matches the bandit's chosen pillar -
    popping something (with a logged warning from the caller) beats skipping
    a day's post entirely."""
    queue = load_queue()
    candidates = [e for e in queue["entries"] if e.get("status") == "queued"]
    if not candidates:
        return None
    candidates.sort(key=lambda e: e.get("queued_at", ""))
    chosen = candidates[0]
    chosen["status"] = "popped"
    save_queue(queue)
    return chosen


def mark_published(item_id: str, video_id: str | None) -> None:
    queue = load_queue()
    for e in queue["entries"]:
        if e.get("id") == item_id:
            e["status"] = "published"
            e["video_id"] = video_id
            e["published_at"] = datetime.now(timezone.utc).isoformat()
            break
    save_queue(queue)


def item_to_pipeline_data(item: dict) -> dict:
    """Adapts a script_queue entry into the exact shape main.py/tts/visuals/
    assemble already consume from script_gen.py's output. `web_searches` is
    set truthy (not a real per-item count) - verification happened upstream
    in Call A, once for the whole idea, not per-video here; main.py's
    "no web search - unverified" warning would otherwise fire on every
    queue-sourced video despite it having been verified."""
    return {
        "topic": item["topic"],
        "title": item["title"],
        "description": item["description"],
        "tags": item["tags"],
        "script": item["script"],
        "shot_list": item["shot_list"],
        "hook_overlay": item.get("hook_overlay"),
        "mood": item.get("mood"),
        "central_claim": item.get("central_claim"),
        "sources": item.get("sources"),
        "web_searches": 1,
        "length_variant": None,
        "closing_question": None,
    }
