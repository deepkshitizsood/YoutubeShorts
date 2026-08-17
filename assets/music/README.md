# Background music

Drop instrumental tracks into the **mood subfolder** they fit. The script LLM tags each
video with a mood and the pipeline picks a matching track:

| Folder | Feel | Fits videos about |
|---|---|---|
| `energetic/` | punchy, driving | surprising or impressive facts |
| `mysterious/` | tense, curious | unexplained or counter-intuitive things |
| `dramatic/` | weighty, cinematic | scale, danger, extremes |
| `uplifting/` | warm, bright | wholesome or positive payoffs |

## Where to get them

**Use the YouTube Audio Library** — [studio.youtube.com](https://studio.youtube.com) →
left sidebar → **Audio library** → **Free music** tab.

This is not an arbitrary preference. YouTube guarantees Audio Library tracks won't be
Content ID claimed. Other "royalty-free" sources don't: Pixabay acknowledges some
contributors register tracks with Content ID, and even genuinely CC0 tracks get
defensively fingerprinted. A claim diverts a video's revenue while it's disputed, which
is the opposite of what this channel is for.

## What to pick

- Filter **Attribution → "Attribution not required"**. Attribution-required tracks need a
  credit line in the description, and descriptions here are LLM-generated per video, so a
  required credit would silently get dropped.
- **Instrumental only** — lyrics compete with the narration.
- **2 min or longer** — tracks are looped to fit, and longer ones hide the loop seam.
- 2–3 tracks per mood is plenty.

Filenames don't matter. `.mp3` and `.wav` are both picked up.

If a mood folder is empty, the pipeline falls back to any other track it can find, and if
there's no music at all it renders narration-only rather than failing.
