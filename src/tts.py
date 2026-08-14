"""Synthesizes narration via the Google Cloud Text-to-Speech REST API and
returns per-word start times (via SSML <mark> timepointing) for caption sync.

Uses a plain API key (REST) rather than the google-cloud SDK/service-account
flow, since that's much simpler to wire up as a single GitHub Actions secret.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import requests

from . import config as cfg

TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"


@dataclass
class WordTiming:
    word: str
    start_seconds: float


@dataclass
class NarrationResult:
    audio_bytes: bytes  # LINEAR16 WAV
    word_timings: list[WordTiming]
    char_count: int


def _build_ssml(script: str) -> tuple[str, list[str]]:
    words = script.split()
    marked = " ".join(f'<mark name="w{i}"/>{w}' for i, w in enumerate(words))
    ssml = f"<speak>{marked}</speak>"
    return ssml, words


def synthesize(config: dict, script: str) -> NarrationResult:
    api_key = cfg.env("GOOGLE_TTS_API_KEY")
    ssml, words = _build_ssml(script)
    providers = config["providers"]["tts"]

    payload = {
        "input": {"ssml": ssml},
        "voice": {
            "languageCode": "en-US",
            "name": providers["voice"],
        },
        "audioConfig": {"audioEncoding": "LINEAR16"},
        "enableTimePointing": ["SSML_MARK"],
    }

    resp = requests.post(TTS_ENDPOINT, params={"key": api_key}, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    audio_bytes = base64.b64decode(data["audioContent"])
    timepoints = {tp["markName"]: tp["timeSeconds"] for tp in data.get("timepoints", [])}

    word_timings = [
        WordTiming(word=w, start_seconds=float(timepoints.get(f"w{i}", 0.0)))
        for i, w in enumerate(words)
    ]

    char_count = len(re.sub(r"\s+", "", script))
    return NarrationResult(audio_bytes=audio_bytes, word_timings=word_timings, char_count=char_count)


def estimated_cost_usd(config: dict, char_count: int) -> float:
    rate = config["providers"]["tts"]["est_cost_per_1k_chars_usd"]
    return (char_count / 1000.0) * rate
