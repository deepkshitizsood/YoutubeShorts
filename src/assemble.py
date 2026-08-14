"""Composites shots (images with Ken Burns motion, or the optional hero video
clip) + narration + background music + word-pop captions into the final MP4,
entirely via ffmpeg subprocess calls (no moviepy dependency, keeps the
GitHub Actions runner fast and light).
"""
from __future__ import annotations

import random
import subprocess
from pathlib import Path

from . import config as cfg
from .tts import WordTiming

FPS = 30
WIDTH, HEIGHT = 1080, 1920


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg command failed:\n{' '.join(cmd)}\n{result.stderr[-4000:]}")


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def compute_shot_windows(shot_list: list[dict], word_timings: list[WordTiming], total_duration: float) -> list[tuple[float, float]]:
    """Returns (start, end) seconds per shot, derived from cumulative word_count
    per shot mapped onto the TTS word timepoints."""
    windows = []
    word_idx = 0
    starts = []
    for shot in shot_list:
        starts.append(word_timings[word_idx].start_seconds if word_idx < len(word_timings) else total_duration)
        word_idx += shot["word_count"]
    ends = starts[1:] + [total_duration]
    for s, e in zip(starts, ends):
        windows.append((s, max(e, s + 0.5)))
    return windows


def render_image_shot(image_path: Path, duration: float, out_path: Path) -> None:
    frames = max(int(duration * FPS), 1)
    zoom_expr = "min(zoom+0.0012,1.4)"
    # x/y keep the crop window centered on the source image as zoom changes -
    # zoompan's default anchors at the top-left corner, which reads as the
    # subject drifting off to a side rather than a straight zoom in/out.
    center_x = "iw/2-(iw/zoom/2)"
    center_y = "ih/2-(ih/zoom/2)"
    vf = (
        f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH*2}:{HEIGHT*2},"
        f"zoompan=z='{zoom_expr}':x='{center_x}':y='{center_y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"format=yuv420p"
    )
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf, "-t", str(duration), "-r", str(FPS),
        "-c:v", "libx264", "-an", str(out_path),
    ])


def render_video_shot(video_path: Path, duration: float, out_path: Path) -> None:
    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},format=yuv420p"
    _run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", vf, "-t", str(duration), "-r", str(FPS),
        "-c:v", "libx264", "-an", str(out_path),
    ])


def concat_clips(clip_paths: list[Path], out_path: Path, tmp_dir: Path) -> None:
    list_file = tmp_dir / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in clip_paths), encoding="utf-8")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(out_path),
    ])


def _ass_timestamp(seconds: float) -> str:
    cs = int(round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginV
Style: Word,DejaVu Sans,96,&H00FFFFFF,&H00000000,&H80000000,1,4,0,2,260
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_word_pop_captions(word_timings: list[WordTiming], total_duration: float, out_path: Path) -> None:
    lines = [ASS_HEADER.format(width=WIDTH, height=HEIGHT)]
    for i, wt in enumerate(word_timings):
        end = word_timings[i + 1].start_seconds if i + 1 < len(word_timings) else total_duration
        end = max(end, wt.start_seconds + 0.1)
        text = wt.word.upper().replace(",", "").replace(".", "")
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(wt.start_seconds)},{_ass_timestamp(end)},Word,,0,0,0,,{text}\n"
        )
    out_path.write_text("".join(lines), encoding="utf-8")


def pick_background_track(music_dir: Path) -> Path | None:
    tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    return random.choice(tracks) if tracks else None


def mux_final(
    silent_video_path: Path,
    narration_wav: Path,
    captions_ass: Path,
    music_path: Path | None,
    music_volume_db: float,
    out_path: Path,
) -> None:
    inputs = ["-i", str(silent_video_path), "-i", str(narration_wav)]
    if music_path:
        inputs += ["-stream_loop", "-1", "-i", str(music_path)]
        filter_complex = (
            f"[2:a]volume={music_volume_db}dB[music];"
            f"[1:a][music]amix=inputs=2:duration=first:weights=1 0.6[aout]"
        )
        audio_map = "[aout]"
    else:
        filter_complex = None
        audio_map = "1:a"

    cmd = ["ffmpeg", "-y", *inputs]
    if filter_complex:
        cmd += ["-filter_complex", filter_complex, "-map", "0:v", "-map", audio_map]
    else:
        cmd += ["-map", "0:v", "-map", audio_map]
    cmd += [
        "-vf", f"ass={captions_ass.as_posix()}",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", str(out_path),
    ]
    _run(cmd)


def assemble_video(
    config: dict,
    shot_list: list[dict],
    shot_media_paths: list[Path],   # image or hero-clip path per shot, same order/length as shot_list
    hero_shot_index: int | None,
    narration_wav_path: Path,
    word_timings: list[WordTiming],
    tmp_dir: Path,
    out_path: Path,
) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    total_duration = ffprobe_duration(narration_wav_path)
    windows = compute_shot_windows(shot_list, word_timings, total_duration)

    clip_paths = []
    for i, (shot, media_path, (start, end)) in enumerate(zip(shot_list, shot_media_paths, windows)):
        duration = end - start
        clip_out = tmp_dir / f"clip_{i:02d}.mp4"
        if i == hero_shot_index:
            render_video_shot(media_path, duration, clip_out)
        else:
            render_image_shot(media_path, duration, clip_out)
        clip_paths.append(clip_out)

    silent_concat = tmp_dir / "silent_concat.mp4"
    concat_clips(clip_paths, silent_concat, tmp_dir)

    captions_path = tmp_dir / "captions.ass"
    build_word_pop_captions(word_timings, total_duration, captions_path)

    music_dir = cfg.REPO_ROOT / config["assembly"]["music_dir"]
    music_path = pick_background_track(music_dir) if music_dir.exists() else None

    mux_final(
        silent_video_path=silent_concat,
        narration_wav=narration_wav_path,
        captions_ass=captions_path,
        music_path=music_path,
        music_volume_db=config["assembly"]["music_volume_db"],
        out_path=out_path,
    )
    return out_path
