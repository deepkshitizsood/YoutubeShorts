"""Renders the same real script in several candidate voices, for auditioning.

Goes through the production tts.synthesize() path on purpose, so a voice that
cannot do SSML <mark> timepointing fails here rather than silently stacking
every caption at t=0 in a real video. Studio and Chirp 3 HD voices fail this
way by design - they are listed below only to prove it.

Cost is negligible: ~550 characters per voice against Neural2's 1M/month free
allowance, so a full sweep is well under 1% of the free tier.

    python -m scripts.sample_voices --out output/voice_samples
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config as cfg  # noqa: E402
from src import queue as q  # noqa: E402
from src import tts  # noqa: E402

# Female en-US voices. Neural2 and WaveNet support <mark>; News voices are
# included to find out, since Google does not document them clearly.
CANDIDATES = [
    "en-US-Neural2-C",
    "en-US-Neural2-E",
    "en-US-Neural2-F",
    "en-US-Neural2-G",
    "en-US-Neural2-H",
    "en-US-Wavenet-F",
    "en-US-News-K",
    "en-US-News-L",
]


def pick_script() -> tuple[str, str]:
    """A real queued script, so the voice is judged on actual material."""
    for entry in q.load_queue()["entries"]:
        if entry.get("status") == "queued":
            return entry["id"], entry["script"]
    raise SystemExit("no queued script to sample with")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/voice_samples")
    ap.add_argument("--voices", nargs="*", default=CANDIDATES)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    script_id, script = pick_script()
    config = cfg.load_config()
    print(f"[voices] Sampling {len(args.voices)} voice(s) on {script_id} "
          f"({len(script)} chars each)\n")

    results = []
    for voice in args.voices:
        patched = copy.deepcopy(config)
        # Pin to exactly this voice: voice_for_today() prefers the `voices`
        # rotation list, which would otherwise override every request here and
        # render the same two voices eight times.
        patched["providers"]["tts"].pop("voices", None)
        patched["providers"]["tts"]["voice"] = voice
        try:
            narration = tts.synthesize(patched, script)
        except Exception as e:
            # Most likely cause is no <mark> support, which disqualifies the
            # voice for this pipeline regardless of how good it sounds.
            print(f"  FAIL  {voice:<18} {str(e)[:110]}")
            results.append({"voice": voice, "ok": False, "error": str(e)[:300]})
            continue
        path = out_dir / f"{voice}.wav"
        path.write_bytes(narration.audio_bytes)
        kb = len(narration.audio_bytes) // 1024
        print(f"  ok    {voice:<18} {kb:>5} KB, {len(narration.word_timings)} word timings")
        results.append({"voice": voice, "ok": True, "file": path.name})

    (out_dir / "_script.txt").write_text(
        f"{script_id}\n\n{script}\n", encoding="utf-8")
    (out_dir / "_results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8")

    usable = [r["voice"] for r in results if r["ok"]]
    print(f"\n[voices] {len(usable)}/{len(args.voices)} usable in this pipeline.")
    if not usable:
        raise SystemExit("no candidate voice supported SSML mark timepointing")


if __name__ == "__main__":
    main()
