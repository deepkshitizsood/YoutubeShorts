# shot_list / mood contract

What `src/visuals.py` and `src/assemble.py` actually read from a script
generation's output today, field by field. This is the contract `gen_scripts.py`
(a later phase) must produce against — derived directly from
`visuals.py::resolve_shot_media` and `assemble.py` (`assemble_video`,
`compute_shot_windows`), not from the prompt that currently asks for it.

## Top-level fields (sibling to `shot_list`, not per-shot)

| Field | Required? | Consumed by | Notes |
|---|---|---|---|
| `shot_list` | required, non-empty | `main.py` (asserts non-empty), `visuals.py`, `assemble.py` | |
| `mood` | optional | `assemble.py::pick_background_track` | Falls back to any track under `music_dir` if absent or unmatched to a folder. `script_gen.py::_validate_mood()` already coerces any invalid value to a configured one, so in practice it's never truly absent by the time it reaches assembly. |
| `hook_overlay` | optional | `assemble.py::build_word_pop_captions` | Skips the on-screen hook caption for the first ~1.2s if absent. |

## Per-shot fields (each dict inside `shot_list`)

| Field | Required? | Consumed by | Notes |
|---|---|---|---|
| `narration_segment` | required | `script_gen.py::_fixup_shot_word_counts` (today) | Must be the exact verbatim span of `script` this shot covers. Today's check is a soft word-count rescale across all shots, not an exact string match — a redesign that hard-asserts exact reconstruction (concatenation of all segments == `script` character-for-character) closes a real gap here. |
| `media_type` | required | `visuals.py::resolve_shot_media` | Must be `"stock"` or `"ai"`. |
| `stock_query` | required only when `media_type == "stock"` | `visuals.py` (`stock.fetch_clip`) | Ignored for `"ai"` shots. Should be short, literal, plain-noun terms — stock libraries match nouns, not prose. |
| `visual_prompt` | **always required**, regardless of `media_type` | `visuals.py::generate_image` | Used as the AI-image prompt both for `"ai"` shots and as the fallback when a `"stock"` shot finds no matching footage (or no `PEXELS_API_KEY` is configured). Must not depict real/identifiable people. |
| `index` | required today | `visuals.py` (output filenames only, e.g. `shot_{idx:02d}.png` / `shot_{idx:02d}.mp4`) | **Not used for ordering** — ordering is list position throughout (`assemble.py` zips `shot_list`/`shot_media_paths`/`shot_kinds` by position, and its own Ken Burns zoom-direction alternation uses the enumeration index `i`, not this field). A soft requirement: could be dropped in favor of `enumerate()` if a future schema prefers not to carry it. |
| `word_count` | required | `assemble.py::compute_shot_windows` | Currently computed/corrected in code from `narration_segment` (`_fixup_shot_word_counts`), never trusted verbatim from the model — `compute_shot_windows` walks cumulative `word_count` per shot to find each shot's start time in the TTS's word-by-word timing (`word_timings`). Any future schema can keep computing this in code from a verbatim shot span, with no need for the model to emit it directly. |

## Why the exact-reconstruction property matters

`word_timings` comes from TTS narration of `data["script"]`, independent of
`shot_list`. `assemble.py::compute_shot_windows` maps each shot's `word_count`
onto positions in that same `word_timings` sequence to derive shot start/end
times. If the shots' texts don't truly reconstruct `script` word-for-word, the
word-count-based windowing silently desyncs visuals from audio — today this is
caught only by a soft rescale, not an explicit assertion, so a drifted shot
split can ship undetected.
