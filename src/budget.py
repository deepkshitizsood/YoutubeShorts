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


def record_spend(ledger: dict, item: str, usd: float, video_id: str | None = None) -> None:
    ledger["entries"].append(
        {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "item": item,
            "usd": round(usd, 4),
            "video_id": video_id,
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


def hero_clip_allowed(ledger: dict, config: dict) -> bool:
    """Auto-disables the optional AI-video hook clip once month-to-date spend
    crosses hero_clip_cutoff_usd, so a heavy month can't blow through the cap."""
    if not config["providers"]["hero_video_clip"].get("enabled", True):
        return False
    spend = month_to_date_spend(ledger)
    return spend < config["budget"]["hero_clip_cutoff_usd"]
