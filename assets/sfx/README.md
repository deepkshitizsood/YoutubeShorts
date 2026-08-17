# Sound effects

| Folder | What | When it plays |
|---|---|---|
| `hook/` | short impact or riser | at t=0, under the hook overlay |
| `transition/` | soft whoosh | at a few major beat changes |

The hook sound is the higher-leverage of the two: the swipe-away decision happens within
roughly 400ms, so an impact landing on the first frame reinforces the hook at exactly the
moment a viewer decides whether to stay.

Transitions are deliberately capped (see `assembly.max_transitions` in `config.yaml`).
A whoosh on all 12–18 cuts is noise — the point is an occasional pattern interrupt, not a
metronome.

## Where to get them

[studio.youtube.com](https://studio.youtube.com) → **Audio library** → **Sound effects**
tab. Search `impact` or `riser` for `hook/`, and `whoosh` for `transition/`.

Same reasoning as the music folder: Audio Library content is guaranteed not to be Content
ID claimed.

Keep them **short** — under ~2s for hooks, under ~1s for whooshes. 2–3 of each is plenty;
the pipeline picks one at random per video so they don't get repetitive.

Empty folders are fine — the pipeline just skips that layer.
