"""Tracks estimated spend per run and enforces the monthly cap from config.yaml.

The ledger is a flat list of {date, item, usd, video_id} entries in
data/spend_ledger.json. Nothing here talks to a billing API - costs are
*estimates* computed from the per-unit prices in config.yaml at the moment
each API call is made, which is accurate enough to keep the pipeline inside
budget without needing reconciliation against provider invoices.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Literal

from . import config as cfg

Status = Literal["ok", "warn", "over"]


def load_ledger() -> dict:
    with open(cfg.SPEND_LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_ledger(ledger: dict) -> None:
    with open(cfg.SPEND_LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)


def record_spend(
    ledger: dict,
    item: str,
    usd: float,
    video_id: str | None = None,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    searches: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> None:
    # Token fields default to 0 for every non-LLM item (tts, images) and were
    # unused entirely before 2026-09-01 - this is the real per-video baseline
    # that a flat $0.09/script estimate never gave us, needed before comparing
    # against the ideation/scripting redesign's real cost.
    ledger["entries"].append(
        {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "item": item,
            "usd": round(usd, 4),
            "video_id": video_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "searches": searches,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_read_tokens": cache_read_tokens,
        }
    )


def month_to_date_spend(ledger: dict, today: date | None = None) -> float:
    # Entries are stamped in UTC, so the month bucket must be UTC too - using
    # local date here mis-buckets spend for several hours around each month
    # boundary when run outside UTC.
    today = today or datetime.now(timezone.utc).date()
    prefix = f"{today.year:04d}-{today.month:02d}"
    return round(
        sum(e["usd"] for e in ledger["entries"] if e["date"].startswith(prefix)), 4
    )


def status(ledger: dict, config: dict) -> Status:
    spend = month_to_date_spend(ledger)
    budget = config["budget"]
    if spend >= budget["monthly_cap_usd"]:
        return "over"
    if spend >= budget["warn_threshold_usd"]:
        return "warn"
    return "ok"


