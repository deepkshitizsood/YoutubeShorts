"""Synthesizes narration via the Google Cloud Text-to-Speech REST API and
returns per-word start times (via SSML <mark> timepointing) for caption sync.

Uses a plain API key (REST) rather than the google-cloud SDK/service-account
flow, since that's much simpler to wire up as a single GitHub Actions secret.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from xml.sax.saxutils import escape as xml_escape

import requests

from . import config as cfg
from .http_util import raise_for_retryable_status, retry_call

TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"  # v1 doesn't support enableTimePointing


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
    """Wraps each word in an SSML <mark> so the response carries per-word timings.

    Words are XML-escaped: an unescaped '&' (R&B, AT&T) or '<' makes the whole
    document malformed, which the API rejects with a 400 - fatal to a run that
    has already paid for script generation.
    """
    words = script.split()
    marked = " ".join(f'<mark name="w{i}"/>{xml_escape(w)}' for i, w in enumerate(words))
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

    def _call() -> dict:
        resp = requests.post(TTS_ENDPOINT, params={"key": api_key}, json=payload, timeout=60)
        raise_for_retryable_status(resp, "Cloud TTS request")
        return resp.json()

    data = retry_call(_call, description="Cloud TTS synthesis")

    audio_bytes = base64.b64decode(data["audioContent"])
    timepoints = {tp["markName"]: tp["timeSeconds"] for tp in data.get("timepoints", [])}

    # Without timepoints every word would silently default to t=0, producing a
    # video where all captions stack on the first frame and every shot window
    # collapses to its minimum - a broken upload rather than a failed run.
    missing = [i for i in range(len(words)) if f"w{i}" not in timepoints]
    if missing:
        raise RuntimeError(
            f"Cloud TTS returned {len(timepoints)} timepoints for {len(words)} words "
            f"({len(missing)} missing). Caption sync would be broken - refusing to continue. "
            f"Check that voice '{providers['voice']}' supports SSML <mark> timepointing."
        )

    word_timings = [
        WordTiming(word=w, start_seconds=float(timepoints[f"w{i}"]))
        for i, w in enumerate(words)
    ]

    char_count = len(re.sub(r"\s+", "", script))
    return NarrationResult(audio_bytes=audio_bytes, word_timings=word_timings, char_count=char_count)


def estimated_cost_usd(config: dict, char_count: int) -> float:
    rate = config["providers"]["tts"]["est_cost_per_1k_chars_usd"]
    return (char_count / 1000.0) * rate
