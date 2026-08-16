"""Composites shots (stock clips, or images with Ken Burns motion) + narration
+ background music + word-pop captions into the final MP4, entirely via ffmpeg
subprocess calls (no moviepy dependency, keeps the GitHub Actions runner fast
and light).
"""
from __future__ import annotations

import random
import subprocess
import sys
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
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"ffprobe could not read duration of {path}: {out.stderr.strip()}")
    return float(out.stdout.strip())


def compute_shot_windows(shot_list: list[dict], word_timings: list[WordTiming], total_duration: float) -> list[tuple[float, float]]:
    """Returns (start, end) seconds per shot, derived from cumulative word_count
    per shot mapped onto the TTS word timepoints.

    Windows are strictly contiguous and non-overlapping: clips are concatenated
    sequentially, so any shot rendered longer than its slot would push every
    later visual out of sync with the narration, and the drift accumulates.
    The first shot is pinned to 0.0 so the visuals cover any lead-in silence.
    """
    starts = []
    word_idx = 0
    for shot in shot_list:
        if word_idx < len(word_timings):
            starts.append(word_timings[word_idx].start_seconds)
        else:
            starts.append(total_duration)
        word_idx += shot["word_count"]

    starts[0] = 0.0

    # Force monotonically increasing starts so no window can be inverted.
    for i in range(1, len(starts)):
        starts[i] = max(starts[i], starts[i - 1])

    ends = starts[1:] + [total_duration]
    return [(s, max(e, s)) for s, e in zip(starts, ends)]


def render_image_shot(image_path: Path, duration: float, out_path: Path, shot_index: int = 0) -> None:
    """Renders a still with Ken Burns motion for exactly `duration` seconds.

    Direction alternates per shot: identical zoom-ins on every shot read as a
    mechanical slideshow, whereas alternating in/out gives the cut rhythm some
    variety at no cost.
    """
    frames = max(int(round(duration * FPS)), 1)
    zoom_in = shot_index % 2 == 0
    # Total travel is held constant regardless of shot length, so short fast cuts
    # move as much as long ones rather than looking frozen.
    if zoom_in:
        zoom_expr = f"min(1+0.18*on/{max(frames - 1, 1)},1.18)"
    else:
        zoom_expr = f"max(1.18-0.18*on/{max(frames - 1, 1)},1.0)"
    # x/y keep the crop window centered on the source image as zoom changes -
    # zoompan's default anchors at the top-left corner, which reads as the
    # subject drifting off to a side rather than a straight zoom in/out.
    center_x = "iw/2-(iw/zoom/2)"
    center_y = "ih/2-(ih/zoom/2)"
    vf = (
        f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH*2}:{HEIGHT*2},"
        f"zoompan=z='{zoom_expr}':x='{center_x}':y='{center_y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"trim=duration={duration},format=yuv420p"
    )
    _run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf, "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out_path),
    ])


def render_video_shot(video_path: Path, duration: float, out_path: Path) -> None:
    """Crops stock footage to vertical and loops it to fill the full window.

    -stream_loop is essential: ffmpeg cannot stretch a source past EOF, so a clip
    shorter than its slot would silently come out short and desync everything
    after it.
    """
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,format=yuv420p"
    )
    _run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(video_path),
        "-vf", vf, "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out_path),
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


# MarginV 420 lifts captions clear of the Shorts UI band (title, channel handle
# and action rail) that overlays the bottom ~15% of the frame on mobile.
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Word,DejaVu Sans,104,&H00FFFFFF,&H00101010,&H80000000,1,5,2,2,80,80,420
Style: Hook,DejaVu Sans,118,&H0000E5FF,&H00101010,&H80000000,1,6,2,5,60,60,0
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

_PUNCT_TO_STRIP = str.maketrans("", "", ',."')


def _ass_escape(text: str) -> str:
    """Neutralizes characters ASS treats as markup."""
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def build_word_pop_captions(
    word_timings: list[WordTiming],
    total_duration: float,
    out_path: Path,
    hook_overlay: str | None = None,
) -> None:
    """Writes word-by-word captions with a scale-pop on each word.

    The pop is a short \\t transform from 120% to 100%, which gives each word a
    visible beat as it lands instead of the previous hard on/off cut.

    `hook_overlay` is burned centre-screen for the first ~1.2s. The swipe-away
    decision happens in well under a second and a large share of Shorts viewing
    starts muted, so the hook has to be readable before any narration is heard.
    """
    lines = [ASS_HEADER.format(width=WIDTH, height=HEIGHT)]

    if hook_overlay:
        text = _ass_escape(hook_overlay.upper().strip())
        lines.append(
            f"Dialogue: 1,{_ass_timestamp(0.0)},{_ass_timestamp(min(1.2, total_duration))},Hook,,0,0,0,,"
            f"{{\\fad(120,180)}}{text}\n"
        )

    for i, wt in enumerate(word_timings):
        end = word_timings[i + 1].start_seconds if i + 1 < len(word_timings) else total_duration
        end = max(end, wt.start_seconds + 0.08)
        text = _ass_escape(wt.word.upper().translate(_PUNCT_TO_STRIP))
        if not text:
            continue
        pop = r"{\fscx120\fscy120\t(0,90,\fscx100\fscy100)}"
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(wt.start_seconds)},{_ass_timestamp(end)},Word,,0,0,0,,{pop}{text}\n"
        )
    out_path.write_text("".join(lines), encoding="utf-8")


def _escape_filter_path(path: Path) -> str:
    """Escapes a path for use inside an ffmpeg filtergraph argument.

    Filtergraphs treat ':' as an option separator, so a Windows drive letter
    would otherwise split the filter arguments.
    """
    return path.as_posix().replace("\\", "/").replace(":", r"\:")


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
    audio_pad_seconds: float = 0.0,
) -> None:
    # loudnorm targets -14 LUFS, the level YouTube normalizes toward, so playback
    # volume is consistent across videos instead of tracking whatever level the
    # TTS happened to return.
    loudnorm = "loudnorm=I=-14:TP=-1.5:LRA=11"

    # Everything runs through one filtergraph (rather than -vf alongside
    # -filter_complex, which is ambiguous about which stream it applies to).
    chains = [f"[0:v]ass={_escape_filter_path(captions_ass)}[v]"]
    inputs = ["-i", str(silent_video_path), "-i", str(narration_wav)]

    # The visual loop tail runs past the end of narration, so the audio is padded
    # with matching silence - otherwise -shortest would trim the tail back off.
    if audio_pad_seconds > 0:
        chains.append(f"[1:a]apad=pad_dur={audio_pad_seconds:.3f}[narr]")
        narration_label = "[narr]"
    else:
        narration_label = "[1:a]"

    if music_path:
        inputs += ["-stream_loop", "-1", "-i", str(music_path)]
        # normalize=0 is essential: amix's default rescales every input by
        # weight/sum(weights), which would drop the narration ~4dB purely as a
        # side effect of adding a music bed.
        chains += [
            f"[2:a]volume={music_volume_db}dB[music]",
            f"{narration_label}[music]amix=inputs=2:duration=first:normalize=0[mixed]",
            f"[mixed]{loudnorm}[aout]",
        ]
    else:
        chains.append(f"{narration_label}{loudnorm}[aout]")

    _run([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(chains),
        "-map", "[v]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest", str(out_path),
    ])


LOOP_TAIL_SECONDS = 0.6


def assemble_video(
    config: dict,
    shot_list: list[dict],
    shot_media_paths: list[Path],   # one media file per shot, same order/length as shot_list
    shot_kinds: list[str],          # "image" or "video", parallel to shot_media_paths
    narration_wav_path: Path,
    word_timings: list[WordTiming],
    tmp_dir: Path,
    out_path: Path,
    hook_overlay: str | None = None,
) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    total_duration = ffprobe_duration(narration_wav_path)
    windows = compute_shot_windows(shot_list, word_timings, total_duration)

    clip_paths = []
    for i, (media_path, kind, (start, end)) in enumerate(zip(shot_media_paths, shot_kinds, windows)):
        duration = end - start
        if duration <= 0.04:  # shorter than a frame; nothing to render
            continue
        clip_out = tmp_dir / f"clip_{i:02d}.mp4"
        if kind == "video":
            render_video_shot(media_path, duration, clip_out)
        else:
            render_image_shot(media_path, duration, clip_out, shot_index=i)
        clip_paths.append(clip_out)

    # Closing on the opening visual makes a replay feel continuous. Rewatches are
    # one of the strongest Shorts ranking signals, so the loop is worth the ~0.6s.
    loop_tail_seconds = 0.0
    if clip_paths:
        loop_tail = tmp_dir / "clip_loop_tail.mp4"
        try:
            if shot_kinds[0] == "video":
                render_video_shot(shot_media_paths[0], LOOP_TAIL_SECONDS, loop_tail)
            else:
                render_image_shot(shot_media_paths[0], LOOP_TAIL_SECONDS, loop_tail, shot_index=0)
            clip_paths.append(loop_tail)
            loop_tail_seconds = LOOP_TAIL_SECONDS
        except Exception as e:
            print(f"[assemble] Loop tail skipped ({e}).", file=sys.stderr)

    silent_concat = tmp_dir / "silent_concat.mp4"
    concat_clips(clip_paths, silent_concat, tmp_dir)

    captions_path = tmp_dir / "captions.ass"
    build_word_pop_captions(word_timings, total_duration, captions_path, hook_overlay=hook_overlay)

    music_dir = cfg.REPO_ROOT / config["assembly"]["music_dir"]
    music_path = pick_background_track(music_dir) if music_dir.exists() else None
    if music_path:
        print(f"[assemble] Background music: {music_path.name}")

    mux_final(
        silent_video_path=silent_concat,
        narration_wav=narration_wav_path,
        captions_ass=captions_path,
        music_path=music_path,
        music_volume_db=config["assembly"]["music_volume_db"],
        out_path=out_path,
        audio_pad_seconds=loop_tail_seconds,
    )
    return out_path
