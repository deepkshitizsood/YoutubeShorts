"""Generates the Hindi audio track for an already-published video.

You add the resulting file to the video yourself in YouTube Studio - YouTube's
API has no endpoint for audio tracks, so that step cannot be automated.

Usage:
    python -m scripts.make_hindi_audio --video-id abc123
    python -m scripts.make_hindi_audio --list-voices

The hard constraint: the Hindi audio plays over a video whose visuals and
burned-in captions were timed to the English narration. So it has to match
that video's length. Hindi spoken aloud usually runs longer than English, so
this measures the result and re-synthesizes at an adjusted speaking rate to
fit. If fitting would need a rate outside the configured bounds, it refuses
and tells you to shorten the script rather than shipping something that
sounds rushed or sluggish.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from src import config as cfg  # noqa: E402
from src import tts  # noqa: E402
from src.upload import youtube_client  # noqa: E402

OUT_DIR = cfg.OUTPUT_DIR / "hindi_audio"


def video_duration_seconds(video_id: str) -> float:
    """The published video's real length, straight from YouTube - more
    reliable than anything we could reconstruct locally, since the rendered
    file isn't kept after the run that made it."""
    resp = youtube_client().videos().list(part="contentDetails", id=video_id).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError(f"No video found with id {video_id!r} on the authenticated channel.")
    iso = items[0]["contentDetails"]["duration"]  # e.g. "PT47S" / "PT1M2S"
    match = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", iso)
    if not match:
        raise RuntimeError(f"Could not parse duration {iso!r} for {video_id}.")
    minutes = int(match.group(1) or 0)
    seconds = float(match.group(2) or 0)
    return minutes * 60 + seconds


def find_hindi_script(video_id: str) -> tuple[str, str]:
    """Looks up the Hindi script for a published video. Returns (title, script_hi)."""
    with open(cfg.CONTENT_HISTORY_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)
    for entry in history:
        if entry.get("video_id") == video_id:
            script_hi = (entry.get("script_hi") or "").strip()
            if not script_hi:
                raise RuntimeError(
                    f"{video_id} has no Hindi script recorded. Hindi scripts are written "
                    f"during the monthly session and saved as 'script_hi'."
                )
            return entry.get("title", video_id), script_hi
    raise RuntimeError(f"{video_id} is not in data/content_history.json.")


def fit_to_duration(text: str, target_seconds: float, hindi_cfg: dict) -> tts.PlainNarration:
    """Synthesizes, measures, then re-synthesizes at a corrected speaking rate.

    One correction pass is enough: speaking rate scales duration close to
    linearly, so rate = measured/target lands within a few hundredths of a
    second. A second pass would cost another call for no real gain.
    """
    voice = hindi_cfg["voice"]
    lang = hindi_cfg["language_code"]
    tolerance = hindi_cfg["duration_tolerance_seconds"]

    first = tts.synthesize_plain(text, voice, lang, speaking_rate=1.0)
    print(f"[hindi] Natural length: {first.duration_seconds:.2f}s | target: {target_seconds:.2f}s")
    if abs(first.duration_seconds - target_seconds) <= tolerance:
        print("[hindi] Already within tolerance - no rate adjustment needed.")
        return first

    needed_rate = first.duration_seconds / target_seconds
    lo, hi = hindi_cfg["min_speaking_rate"], hindi_cfg["max_speaking_rate"]
    if not (lo <= needed_rate <= hi):
        over_under = "longer" if needed_rate > 1 else "shorter"
        raise RuntimeError(
            f"Hindi audio is {abs(1 - needed_rate) * 100:.0f}% {over_under} than the video "
            f"({first.duration_seconds:.2f}s vs {target_seconds:.2f}s). Fitting it would need "
            f"speaking rate {needed_rate:.2f}, outside the allowed {lo}-{hi} range, which would "
            f"sound wrong. Rewrite the Hindi script {'shorter' if needed_rate > 1 else 'longer'} "
            f"and try again."
        )

    print(f"[hindi] Re-synthesizing at speaking rate {needed_rate:.3f} to fit.")
    fitted = tts.synthesize_plain(text, voice, lang, speaking_rate=needed_rate)
    drift = abs(fitted.duration_seconds - target_seconds)
    print(f"[hindi] Fitted length: {fitted.duration_seconds:.2f}s (off by {drift:.2f}s)")
    if drift > tolerance:
        print(
            f"[hindi] WARNING: still {drift:.2f}s off target after adjustment - "
            f"listen before uploading.",
            file=sys.stderr,
        )
    return fitted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", help="The published video to make a Hindi track for")
    parser.add_argument(
        "--list-voices", action="store_true",
        help="Print the hi-IN voices Google actually offers, then exit",
    )
    args = parser.parse_args()

    config = cfg.load_config()
    hindi_cfg = config["providers"]["tts_hindi"]

    if args.list_voices:
        for v in tts.list_voices(hindi_cfg["language_code"]):
            names = ", ".join(v.get("languageCodes", []))
            print(f"{v.get('name'):<28} {v.get('ssmlGender', '?'):<8} {names}")
        return

    if not args.video_id:
        parser.error("--video-id is required (or use --list-voices)")

    title, script_hi = find_hindi_script(args.video_id)
    target = video_duration_seconds(args.video_id)
    print(f"[hindi] {args.video_id} - {title}")

    narration = fit_to_duration(script_hi, target, hindi_cfg)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{args.video_id}_hi.wav"
    out_path.write_bytes(narration.audio_bytes)

    cost = tts.estimated_cost_usd(config, narration.char_count)
    print(f"\n[hindi] Wrote {out_path} (~${cost:.4f})")
    print("[hindi] Add it in YouTube Studio: open the video -> Audio/Dub -> "
          "upload this file as the Hindi track.")


if __name__ == "__main__":
    main()
