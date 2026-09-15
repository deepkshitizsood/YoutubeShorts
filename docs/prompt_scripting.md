# Call B — Batch scripting prompt

**Run:** fortnightly, matched to ideation's cadence. One call, 20 scripts (~2 weeks at
1/day plus slack for retries and pillar mismatches).
**Model:** small (Haiku 4.5). Tools **OFF**. Web search **OFF**. Non-agentic — one request,
one response, no loop.
**Input:** `style.md` as cached system prompt + 20 approved concepts.
**Output:** JSON array of scripts, each including its shot list.

This call is deliberately dumb. All the judgment already happened in Call A and at the
gate. If output quality drops here, fix the concept or `style.md` — do not upgrade
the model.

---

## System prompt (cached)

```
{{CONTENTS OF style.md}}
```

That's the whole system prompt. Nothing else. On the API, mark it with
`cache_control: {"type": "ephemeral"}` — you'll pay full price for it once a week and
~10% on every reuse.

## User prompt

Write the narration for each of the following approved concepts. One script per
concept, in the same order.

Every script must follow `style.md` exactly: 110–135 words, four beats, the assigned
hook pattern, no banned phrases, numbers spelled as spoken.

Use the supplied `hook` as the opening line. You may tighten its wording but not
change its angle or its claim. The supplied `anchor_spoken` must appear **verbatim**
somewhere in `script` — restate it exactly, do not round it, recompute it, or reword the
number, even if a slightly different phrasing would read more naturally.

After writing `script`, split it into shots: divide it into short spans of ~2-3 seconds
of narration each (roughly matching the target shot count implied by its length), and for
each shot decide the visual. The `narration_segment` fields, concatenated in order with a
single space between each, must reconstruct `script` **EXACTLY** (same words, same order,
nothing skipped or duplicated, no added punctuation) — this is checked in code and a
mismatch fails the whole item.

media_type rules per shot:
- Use `"stock"` for concrete, filmable subjects real footage exists for: planets, moons,
  stars, spacecraft, telescopes, landscapes, everyday objects used for scale comparisons.
  Give a simple, literal `stock_query` — stock libraries match plain nouns, not prose.
- Use `"ai"` for abstract, historical, microscopic, hypothetical, or otherwise unfilmable
  ideas, and anything needing a specific invented composition.
- `visual_prompt` is **always required**, regardless of `media_type` — it is the fallback
  when no stock footage matches. Must not depict real/identifiable people; use
  illustrative, abstract, nature, object, or generic-figure imagery instead.

Batch-level constraints, checked across all 20 before you output:
- No hook pattern appears more than three times.
- No two scripts share a loop-closer shape.
- "Universe" appears in at most two hooks.
- No sentence is reused across scripts.

Concepts:

```json
{{JSON array of approved concepts — id, title, hook, spine, anchor, anchor_spoken, mechanism, consequence, pattern, confidence}}
```

Output a JSON array. No commentary, no markdown fences, no preamble:

```json
[{"id":"cb-0001","script":"","word_count":0,"pattern_used":"","mood":"","hook_overlay":"",
  "shot_list":[{"index":0,"narration_segment":"","media_type":"stock|ai",
                "stock_query":"","visual_prompt":""}]}]
```

`hook_overlay` is the text burned over the opening frame — which on Shorts *is* the
thumbnail. 2-6 words, names the subject, opens a curiosity gap ("SATURN WOULD FLOAT").
Never a bare noun; never sliced from the script. Shot 0's `visual_prompt` must show the
most dramatic image in the story, not a minor prop. Full rules in `style.md`.

`mood` is exactly one of the channel's configured moods (see `config.yaml`'s
`content.moods`) — the emotional register of this fact, used to pick a matching music bed.

`word_count` is your own count of the words in `script`. If it falls outside 110–135,
revise before outputting — do not output a script you know is out of spec.

---

## Validation (in code, after the call — no model)

```python
BANNED = ["did you know", "imagine if", "buckle up", "mind-blowing",
          "you won't believe", "here's the crazy part", "let's dive in",
          "let that sink in", "what if i told you", "in this video",
          "scientists were shocked", "this changes everything"]

def reconstruct(shot_list):
    return " ".join(s["narration_segment"] for s in shot_list)

def validate(concept, s):
    words = len(s["script"].split())
    assert 110 <= words <= 135,           f'{s["id"]}: {words} words'
    assert not re.search(r"\d", s["script"]), f'{s["id"]}: digits in narration'
    low = s["script"].lower()
    assert not any(b in low for b in BANNED), f'{s["id"]}: banned phrase'
    # Anchor-drift guard: the verified number must survive into narration unchanged -
    # a prompt instruction alone is the weakest kind of guarantee, so this is a hard
    # substring check, not a request.
    assert concept["anchor_spoken"].lower() in low, f'{s["id"]}: anchor_spoken not found verbatim'
    # Shot-reconstruction guard: catches a hallucinated, dropped, or reworded shot before
    # it silently desyncs visuals from audio downstream (see docs/shot_list_contract.md).
    assert reconstruct(s["shot_list"]) == s["script"], f'{s["id"]}: shot_list does not reconstruct script exactly'
    assert s["shot_list"], f'{s["id"]}: empty shot_list'
    for shot in s["shot_list"]:
        assert shot["media_type"] in ("stock", "ai"), f'{s["id"]}: bad media_type'
        assert shot.get("visual_prompt"), f'{s["id"]}: missing visual_prompt'
        if shot["media_type"] == "stock":
            assert shot.get("stock_query"), f'{s["id"]}: stock shot missing stock_query'
```

Anything that fails gets re-requested **individually** (that one concept, not the whole
batch) — a handful of retries costs far less than routing the whole batch through a
bigger model. Still failing after a couple of attempts: leave the concept `approved` in
the idea bank rather than block the rest of the batch; it's picked up again next
scripting run.

---

## Not the model's job

Do these in Python, on the validated batch. None of it needs an LLM:

| Artifact | How |
|---|---|
| YouTube title | `concept["title"]`, already written in Call A |
| Description | f-string template + `consequence` + `source` |
| Tags / hashtags | fixed set per `cluster`, from a dict, through `keywords.normalize_tags` |
| Filename / topic slug | derived from `concept["title"]` |
| Thumbnail overlay text | first 4 words of the winning hook, uppercased |
| Upload schedule | `main.py` pops one item off `data/script_queue.json` via `src/queue.py` |
| Dedup | already covered by `strategy.recent_titles()` / `used_topics()` at ideation time - no separate ledger needed |

On a normal day the pipeline makes **zero LLM calls** — it pops one finished script
off the queue, renders, and uploads.
