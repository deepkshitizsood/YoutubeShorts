"""Loads config.yaml and resolves repo-relative paths. Single source of truth for settings."""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
ASSETS_DIR = REPO_ROOT / "assets"
OUTPUT_DIR = REPO_ROOT / "output"

PERFORMANCE_LOG_PATH = DATA_DIR / "performance_log.json"
SPEND_LEDGER_PATH = DATA_DIR / "spend_ledger.json"
CONTENT_HISTORY_PATH = DATA_DIR / "content_history.json"


@lru_cache(maxsize=1)
def load_config() -> dict:
    with open(REPO_ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env(name: str, required: bool = True) -> str | None:
    val = os.environ.get(name)
    if required and not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it locally (.env) or as a GitHub Actions secret."
        )
    return val


def ensure_dirs() -> None:
    """Creates the directories and state files the pipeline assumes exist.

    The loaders all open these files directly, so a fresh clone missing any of
    them would die on FileNotFoundError before the run even starts.
    """
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    for path, initial in (
        (PERFORMANCE_LOG_PATH, "[]\n"),
        (CONTENT_HISTORY_PATH, "[]\n"),
        (SPEND_LEDGER_PATH, '{\n  "entries": []\n}\n'),
    ):
        if not path.exists():
            path.write_text(initial, encoding="utf-8")
