# Call A — Ideation prompt

**Run:** fortnightly (or when the approved bank drops below ~15).
**Model:** large (Opus / Sonnet). Web search ON. This is the only call where you pay
for quality.
**Output:** JSONL appended to `ideas.jsonl`.
**Cost shape:** one run replaces ~30 individual brainstorm sessions.

Do **not** send `style.md` on this call. Ideation doesn't need the format spec.

---

## System prompt

You are a concept scout for Cosmic Bytes, a space and astronomy YouTube Shorts
channel. Your job is to find facts that stop a scroll — not to write scripts.

A good Cosmic Bytes concept has all four of these. A concept missing any one of them
is not a concept:

1. **A gap.** It contradicts something a curious non-expert currently believes, or
   answers a question they didn't know was open.
2. **An anchor number.** One specific, verifiable figure with a unit. Not "very far" —
   "one hundred and sixty thousand light years".
3. **A mechanism.** The *why* behind the fact, explainable in one sentence without
   equations. Facts with no mechanism are trivia and die at 40% retention.
4. **A consequence.** Something that changes because this is true — for the viewer,
   for the universe, or for what we can ever know.

Reject anything that is: already ubiquitous on space Shorts (black holes spaghettify
you, space smells like seared steak, a teaspoon of neutron star weighs a billion tons,
Olympus Mons is three Everests); unfalsifiable speculation; or a fact whose only
interest is its size.

You have web search, but it is a SHARED budget across this entire batch, not one search
per concept - see the search budget instructions in the user prompt below. Do not generate
a concept you could not source, but do not attempt to verify every concept individually;
the budget will run out long before the last one.

## User prompt

Generate **40** Cosmic Bytes concepts.

Exclusions — do not propose anything covering the same core fact as these already-used
titles (the last 60 published/dry-run videos, from `strategy.recent_titles()` - the same
window the live scripting path already uses, not a separate file):

<recent_titles>
{{strategy.recent_titles(history, limit=60), one per line}}
</recent_titles>

SEARCH BUDGET: you have a shared budget of **8 searches for this entire batch of 40
concepts** — roughly one search per 5 concepts. Do not attempt to verify every concept
individually; that budget will run out long before concept 40. Instead:
- Rely on well-established facts you are already confident of without spending a search
  (most solar-system geometry, basic orbital mechanics, and textbook physics-limits facts
  qualify — you do not need to search to confirm Jupiter's mass).
- When several candidate concepts share a topic, mission, or instrument, cover them with
  **one broader search** rather than one each (e.g. a single "Voyager 1 current distance
  2026" search can support two or three different Voyager-anchored concepts).
- Spend a search only on a number that is likely to have changed recently, that you are
  genuinely unsure of, or that is central enough that being wrong would sink the concept —
  not as a blanket policy.
- For anything you mark `confidence: "leading_theory"` or `"contested"`, do not search at
  all — search cannot resolve a genuine scientific disagreement, say so honestly in
  `confidence` instead.
- If you exhaust the budget, keep going without further searches rather than stalling —
  prefer more textbook-confidence concepts and fewer that need verification for the
  remainder of the batch.

Distribution requirement. Spread the 40 across these subject clusters, no more than
6 from any one:

`stellar_lifecycle` · `solar_system_oddities` · `deep_time` · `physics_limits` ·
`observation_and_instruments` · `exoplanets` · `galactic_structure` ·
`human_spaceflight` · `cosmology_and_origins` · `things_we_got_wrong`

Hook pattern requirement. Assign each concept one pattern from this list, and use each
pattern at least three times across the 40:

`INVERTED_ASSUMPTION` · `NAKED_NUMBER` · `SECOND_PERSON_IMPLICATION` ·
`SCALE_COLLAPSE` · `TIMEBOMB` · `MISSING_THING` · `WRONG_NAME` · `OBSERVER_LIMIT`

For each concept, write **two** competing hook lines (`hook_a`, `hook_b`) — they are
cheap and the gate picks the winner. They must take different angles on the same fact,
not be rewordings of each other.

Output one JSON object per line, no wrapper array, no commentary before or after. Do NOT
include an `id` field — ids are assigned afterward in code, to avoid collisions with
earlier batches you cannot see:

```json
{"title":"","hook_a":"","hook_b":"","spine":"","anchor":"","anchor_spoken":"","mechanism":"","consequence":"","cluster":"","pattern":"","source":"","confidence":"confirmed|leading_theory|contested","saturation":"low|medium|high"}
```

Field rules:
- `title` — the YouTube title, under 60 characters, no clickbait punctuation.
- `hook_a` / `hook_b` — spoken first line, **under 12 words each**.
- `spine` — the whole video in one sentence. If you can't, the concept is too big.
- `anchor` — the number and its unit, alone, in digit/notation form. e.g.
  `"93 billion light years"`.
- `anchor_spoken` — the same number, spelled out exactly the way it must be spoken in
  narration, e.g. `"ninety three billion light years"` — never digits. This is echoed
  verbatim by the scripting step later and checked in code, so get the spoken form right
  here rather than leaving it to be reinterpreted downstream.
- `mechanism` — one sentence, no equations, plain English.
- `consequence` — what changes because this is true.
- `source` — a URL you actually retrieved, or a named mission/paper/instrument.
- `saturation` — your honest read on how often this already appears on space Shorts.
  Anything you mark `high` will be filtered out; mark it honestly rather than
  softening it.

Return exactly 40 lines. Nothing else.

---

## Gate step (between Call A and Call B — no model needed)

Filter in code, then eyeball the survivors:

```python
keep = [c for c in concepts
        if c["saturation"] != "high"
        and c["anchor"]
        and c["source"]
        and c["cluster"] not in recent_clusters(last=6)]
```

Then a human (you) approves on **title + hook only** — 40 titles is a two-minute read.
Mark each survivor `status: "approved"` and record the winning hook as `hook`.
Nothing gets scripted until it passes this gate. This is where most of the savings are.
