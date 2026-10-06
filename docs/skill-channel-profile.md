# Channel profile — Cosmic Bytes (@CosmicByttes)

**Load this before any sub-skill. It pre-answers the Context-Gathering Protocol
and overrides specific playbook benchmarks that are wrong for this channel.**

> Local override file. A reinstall of claude-youtube will delete it — it lives
> outside the upstream repo's file set. Re-copy it after any skill update.

## Context (do not ask the user for these again)

| Input | Value |
|---|---|
| Niche | Space and astronomy facts — one counter-intuitive fact per video |
| Channel type | **Shorts-First** (`templates/shorts-first-channel.md`) |
| Size tier | New (<1K subs) — confirm once `YOUTUBE_API_KEY` is set |
| Primary goal | **Growth** (distribution is the constraint, not content quality) |
| Handle / URL | `@CosmicByttes` |
| Top market | India (~21.6% of views) |

## Operating model — this is a factory, not a creator

This channel is produced by an **automated pipeline**
(`C:\Users\DEEP\Desktop\Youtube Agent`), not by a person editing videos:

- Scripts are hand-written monthly in batches and queued in
  `data/script_queue.json`; the daily GitHub Actions run pops one.
- Voice is Google Cloud TTS, visuals are Gemini-generated images plus Pexels
  stock, assembly is ffmpeg, upload is the YouTube Data API.
- Spend is tracked per video against a hard monthly cap.

**Consequences for every sub-skill:**

1. Never recommend anything that requires a human to film, record voice, or
   edit. Recommendations must be expressible as a config change, a code change,
   or a change to the written script batch.
2. Every recommendation should name the file it lands in. "Shorten titles" is
   not actionable; "cap `title` at 40 chars in `gen_scripts.templatize()`" is.
3. Changes cost money to test — roughly **$0.28 per rendered video**. Prefer
   metadata-only changes, which need no re-render, over anything requiring one.

## Real performance data — use this, not estimates

`data/performance_log.json` holds 63 videos of real analytics (views, average
view percentage, average view duration, likes, comments, shares). **Prefer it
over the skill's execution scripts**, which need credentials the user hasn't
set, and over asking the user to paste screenshots.

Baseline as of 2026-10-06: views median **975**, ceiling **1,373**; completion
median **68.8%**; engagement median **3.61%**.

---

# Playbook overrides

These three entries in `references/shorts-playbook.md` are wrong *for this
channel*. Apply the override, not the published benchmark.

## 1. Thumbnails — lower priority than the playbook implies

The playbook says thumbnails are irrelevant in the Shorts feed because Shorts
auto-play. That is correct, and it means **the custom-thumbnail work on this
channel is low priority**, not the blocker it was treated as.

Thumbnails still matter for channel-page browsing, YouTube search results, and
external shares — so they are worth having, but never worth prioritising above
a completion-rate or hook change.

The channel is not phone-verified, so `thumbnails.set` returns 403 on every
upload. This is logged and ignored by design; it does not fail the upload and
it does not need fixing urgently.

## 2. Music revenue split — does not apply here

The playbook's table ("1 track = 50% of pool allocation") describes tracks
licensed through the **Shorts commercial music picker**. This channel uses
**YouTube Audio Library** tracks (Chris Haugen, Dyalla, Patrick Patrikios,
Everet Almond, Schwartzy, Ezra Lipp) stored locally in `assets/music/`, which
are royalty-free and do not trigger that split.

Never recommend removing background music on revenue grounds. The channel is
also not yet in the Partner Programme, so the split is moot either way.

## 3. "Shorter = higher completion" — contradicted by this channel's own data

The playbook's bimodal peaks (13s / 60s) and the general shorter-is-better
reasoning conflict with what this channel measures. Its bandit reports:

```
Length variants: long=3.797 (n=22), short=3.281 (n=26)
```

**Longer videos score better here.** Current runtimes cluster at 29–44s.

Do not recommend cutting length on the playbook's authority alone. Recommend an
explicit A/B instead — ship deliberately short (~20s) and deliberately long
(~55s) variants and let the existing bandit in `src/strategy.py` settle it.

---

# What the skill cannot do for this channel

State this plainly rather than implying otherwise. The skill produces advice;
the pipeline produces videos. The skill does **not** generate voice, images or
video, does not assemble or upload anything, does not run on a schedule, and
does not track spend. Any recommendation it makes has to be implemented in the
pipeline to reach a viewer.

# Known gaps

- **Viewed vs Swiped Away is not collected.** It is the playbook's #4 signal
  and replaces CTR entirely for Shorts, and this channel cannot see it. Treat
  any claim about hook performance as inference from completion rate, and say
  so, until `src/analytics.py` collects it.
- Captions currently sit low in frame, where the YouTube control bar overlaps
  them. Known, deferred by the user.
