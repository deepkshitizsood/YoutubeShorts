# Call B — Batch scripting prompt

**Run:** weekly. One call, 21 scripts (a full week at 3/day).
**Model:** small (Haiku). Tools **OFF**. Web search **OFF**. Non-agentic — one request,
one response, no loop.
**Input:** `style.md` as cached system prompt + 21 approved concepts.
**Output:** JSON array of scripts.

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
change its angle or its claim.

Batch-level constraints, checked across all 21 before you output:
- No hook pattern appears more than three times.
- No two scripts share a loop-closer shape.
- "Universe" appears in at most two hooks.
- No sentence is reused across scripts.

Concepts:

```json
{{JSON array of approved concepts — id, title, hook, spine, anchor, mechanism, consequence, pattern, confidence}}
```

Output a JSON array. No commentary, no markdown fences, no preamble:

```json
[{"id":"cb-0001","script":"","word_count":0,"pattern_used":""}]
```

`word_count` is your own count of the words in `script`. If it falls outside 110–135,
revise before outputting — do not output a script you know is out of spec.

---

## Validation (in code, after the call — no model)

```python
BANNED = ["did you know", "imagine if", "buckle up", "mind-blowing",
          "you won't believe", "here's the crazy part", "let's dive in",
          "let that sink in", "what if i told you", "in this video",
          "scientists were shocked", "this changes everything"]

def validate(s):
    words = len(s["script"].split())
    assert 110 <= words <= 135,           f'{s["id"]}: {words} words'
    assert not re.search(r"\d", s["script"]), f'{s["id"]}: digits in narration'
    low = s["script"].lower()
    assert not any(b in low for b in BANNED), f'{s["id"]}: banned phrase'
```

Anything that fails gets re-requested individually — a handful of retries costs far
less than routing the whole batch through a bigger model.

---

## Not the model's job

Do these in Python, on the validated batch. None of it needs an LLM:

| Artifact | How |
|---|---|
| YouTube title | `concept["title"]`, already written in Call A |
| Description | f-string template + `consequence` + `source` |
| Tags / hashtags | fixed set per `cluster`, from a dict |
| Filename | `f"{id}_{slug(title)}.txt"` |
| Thumbnail text | first 4 words of the hook, uppercased |
| Upload schedule | `publish.py` pops 3/day off the queue |
| Dedup ledger | append `title` to `used_titles.txt` on publish |

On a normal day the pipeline makes **zero LLM calls** — it pops three finished scripts
off the queue, renders, and uploads.
