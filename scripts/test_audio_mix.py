"""Exercises the audio filtergraph end-to-end with synthetic assets.

The mix (sidechain ducking + delayed SFX layers + loudnorm) is the most complex
ffmpeg in the project, ffmpeg only exists on the CI runner, and a mistake here
would surface as a broken public upload. This builds throwaway tones for every
layer and asserts the muxed result is actually playable, so the graph can be
verified without waiting on real music being added.

Usage (on a machine with ffmpeg):
    python -m scripts.test_audio_mix
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from src import assemble
from src.config import load_config

DURATION = 6.0


def _synth(path: Path, spec: str, seconds: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"{spec}:duration={seconds}",
         "-c:a", "pcm_s16le" if path.suffix == ".wav" else "libmp3lame", str(path)],
        check=True, capture_output=True,
    )


def _silent_video(path: Path, seconds: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=540x960:d={seconds}",
         "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
        check=True, capture_output=True,
    )


def _probe(path: Path, stream: str, entries: str) -> str:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", stream,
         "-show_entries", entries, "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def main() -> None:
    cfg = load_config()
    tmp = Path(tempfile.mkdtemp())

    narration = tmp / "narration.wav"
    music = tmp / "music.mp3"
    hook = tmp / "hook.mp3"
    whoosh = tmp / "whoosh.mp3"
    video = tmp / "silent.mp4"
    captions = tmp / "captions.ass"
    out = tmp / "out.mp4"

    # Amplitude-modulated tone stands in for speech so the sidechain has
    # something with real dynamics to duck against.
    _synth(narration, "sine=frequency=220:sample_rate=44100", DURATION)
    _synth(music, "sine=frequency=440:sample_rate=44100", DURATION)
    _synth(hook, "sine=frequency=880:sample_rate=44100", 0.5)
    _synth(whoosh, "sine=frequency=660:sample_rate=44100", 0.4)
    _silent_video(video, DURATION + 0.6)
    captions.write_text(
        assemble.ASS_HEADER.format(width=assemble.WIDTH, height=assemble.HEIGHT),
        encoding="utf-8",
    )

    cases = {
        "narration only": dict(music_path=None, hook_sfx=None, transition_sfx=[]),
        "music + ducking": dict(music_path=music, hook_sfx=None, transition_sfx=[]),
        "hook sfx only": dict(music_path=None, hook_sfx=hook, transition_sfx=[]),
        "full stack": dict(
            music_path=music, hook_sfx=hook,
            transition_sfx=[(whoosh, 2.0), (whoosh, 4.0)],
        ),
    }

    failures = []
    for name, kwargs in cases.items():
        try:
            assemble.mux_final(
                silent_video_path=video,
                narration_wav=narration,
                captions_ass=captions,
                music_volume_db=cfg["assembly"]["music_volume_db"],
                out_path=out,
                audio_pad_seconds=0.6,
                assembly_cfg=cfg["assembly"],
                **kwargs,
            )
            codec = _probe(out, "a:0", "stream=codec_name")
            duration = float(_probe(out, "v:0", "format=duration"))
            if not codec:
                raise AssertionError("output has no audio stream")
            # narration + 0.6s pad, allowing for encoder frame rounding
            if not (DURATION + 0.3) <= duration <= (DURATION + 1.2):
                raise AssertionError(f"unexpected duration {duration:.2f}s")
            print(f"  PASS  {name:<18} audio={codec} duration={duration:.2f}s")
        except Exception as e:
            detail = e.stderr[-600:] if isinstance(e, subprocess.CalledProcessError) and e.stderr else e
            print(f"  FAIL  {name:<18} {detail}")
            failures.append(name)

    print()
    if failures:
        print(f"AUDIO MIX TEST FAILED: {', '.join(failures)}")
        sys.exit(1)
    print("AUDIO MIX TEST PASSED - all layer combinations render")


if __name__ == "__main__":
    main()
