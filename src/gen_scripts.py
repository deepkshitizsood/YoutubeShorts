"""Call B - batch scripting. Turns already-approved, already-verified concepts
from data/idea_bank.jsonl into finished scripts (narration + shot list), using
a cheap, non-agentic Claude Haiku 4.5 call with no tools and no web search -
all the judgment already happened in Call A and the human gate between them.

Run manually / via .github/workflows/scripting_batch.yml:
    python -m src.gen_scripts

See docs/prompt_scripting.md for the prompt this implements, and
docs/shot_list_contract.md for the exact fields visuals.py/assemble.py need.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic

from . import config as cfg
from . import budget, keywords
from .gen_ideas import load_idea_bank, save_idea_bank
from .http_util import RetryableError, retry_call
from .queue import append_script_queue
from .script_gen import LLMUsage, _enforce_title_length, _validate_mood

STYLE_MD_PATH = cfg.REPO_ROOT / "style.md"

BANNED_PHRASES = [
    "did you know", "imagine if", "buckle up", "mind-blowing", "mind-bending",
    "you won't believe", "here's the crazy part", "scientists were shocked",
    "scientists were stunned", "in this video", "let's dive in", "let that sink in",
    "prepare to have your mind blown", "but wait, it gets weirder", "the truth is",
    "what if i told you", "little did they know", "this changes everything",
    "literally", "insane", "absolutely wild",
]
# Only ever the first thing said - harmless mid-script, fatal as an opener.
BANNED_OPENERS = ["did you know", "in this video", "imagine", "the truth is",
                  "here's something", "scientists were shocked", "you won't believe"]
BANNED_CLOSERS = ["like and subscribe", "follow for more", "comment below",
                  "subscribe for more", "hit the like"]

# Runtime, not word count, is the real limit: ~2.5 words per spoken second.
WORDS_PER_SECOND = 2.5
RUNTIME_MIN_SECONDS, RUNTIME_MAX_SECONDS = 25.0, 45.0
WORD_COUNT_MIN = int(RUNTIME_MIN_SECONDS * WORDS_PER_SECOND)   # 62
WORD_COUNT_MAX = int(RUNTIME_MAX_SECONDS * WORDS_PER_SECOND)   # 112

BEAT_ORDER = ["hook", "turn", "mechanism", "spike", "loop"]
FORMAT_LETTERS = {"A", "B", "C", "D", "E"}
HOOK_MAX_WORDS = 12
TITLE_MAX_CHARS = 70
MIN_SECOND_PERSON = 2

# Phrases that historically hid a real error. Not auto-fail - a human has to
# look, because each is legitimate in some contexts and wrong in others.
TRAP_PATTERNS = [
    (r"\bever built\b", "expired superlative? (was true of Hubble, not since Webb)"),
    (r"\bmost powerful\b", "expired superlative?"),
    # "only"/"first" need the article to be a superlative CLAIM - bare "only
    # two hundred days" or "First Mercury goes" are grammar, not claims.
    (r"\bthe (first|only)\b", "superlative claim - does it still hold?"),
    (r"\b(largest|biggest|fastest|longest|hottest|densest|brightest)\b",
     "superlative - does it still hold?"),
    (r"everything you (have )?ever", "overstated universal - is it literally all?"),
    # Deliberately broad: this exact trap shipped a false statement once
    # (Venus sidereal day in the hook, solar day in the closer). A noisy
    # warning beats a silent error.
    (r"\bday\b[^.?!]*\byear\b|\byear\b[^.?!]*\bday\b", "day vs year - sidereal or solar? say which"),
]
SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|yours|yourself)\b", re.I)

# Fixed per-cluster tags (SEO breadth + specificity), combined with BASE_TAGS.
# A deterministic dict, not a model call - see docs/prompt_scripting.md's
# "not the model's job" table.
CLUSTER_TAGS: dict[str, list[str]] = {
    "stellar_lifecycle": ["stars", "supernova", "star death"],
    "solar_system_oddities": ["solar system", "planets", "planet facts"],
    "deep_time": ["universe age", "cosmic time", "deep time"],
    "physics_limits": ["physics facts", "science facts", "physics"],
    "observation_and_instruments": ["telescope", "space observation", "astronomy tools"],
    "exoplanets": ["exoplanets", "alien planets", "habitable zone"],
    "galactic_structure": ["galaxy", "milky way", "galaxies"],
    "human_spaceflight": ["space missions", "nasa", "astronauts"],
    "cosmology_and_origins": ["big bang", "origin of universe", "cosmology"],
    "things_we_got_wrong": ["space myths", "mythbusting", "you were taught wrong"],
}
BASE_TAGS = ["space facts", "astronomy", "space", "universe", "didyouknow"]

USER_PROMPT_TEMPLATE = """Write the narration for each of the following approved concepts. One
script per concept, in the same order.

Every script must follow the style spec exactly: {word_min}-{word_max} words, four beats,
the assigned hook pattern, no banned phrases, numbers spelled as spoken.

Use the supplied `hook` as the opening line. You may tighten its wording but not change its
angle or its claim. The supplied `anchor_spoken` must appear verbatim somewhere in `script` -
restate it exactly, do not round it, recompute it, or reword the number.

After writing `script`, split it into shots: divide it into short spans of ~2-3 seconds of
narration each, and for each shot decide the visual. The `narration_segment` fields,
concatenated in order with a single space between each, must reconstruct `script` EXACTLY
(same words, same order, nothing skipped or duplicated, no added punctuation).

media_type rules per shot:
- Use "stock" for concrete, filmable subjects real footage exists for: planets, moons,
  stars, spacecraft, telescopes, landscapes, everyday objects used for scale comparisons.
  Give a simple, literal stock_query - stock libraries match plain nouns, not prose.
- Use "ai" for abstract, historical, microscopic, hypothetical, or otherwise unfilmable
  ideas, and anything needing a specific invented composition.
- visual_prompt is ALWAYS required regardless of media_type - it is the fallback when no
  stock footage matches. Must not depict real/identifiable people.

Batch-level constraints, checked across all {n} before you output:
- No hook pattern appears more than three times.
- No two scripts share a loop-closer shape.
- "Universe" appears in at most two hooks.
- No sentence is reused across scripts.

Concepts:
```json
{concepts_json}
```

THE FIRST SHOT IS THE THUMBNAIL. On Shorts there is no separate thumbnail - the frame
people see while scrolling is the opening frame of the video. So shot 0's visual_prompt
must show the most dramatic image in the story, not a minor prop the first sentence
happens to mention. And `hook_overlay` is the text burned over it: 2-6 words that name
the subject and open a curiosity gap ("SATURN WOULD FLOAT"), never a bare noun.

Output a JSON array. No commentary, no markdown fences, no preamble:
[{{"id":"cb-0001","script":"","word_count":0,"pattern_used":"","mood":"","hook_overlay":"",
  "shot_list":[{{"index":0,"narration_segment":"","media_type":"stock|ai",
                "stock_query":"","visual_prompt":""}}]}}]

`mood` is exactly one of: {moods}.
`word_count` is your own count of the words in `script` - if it falls outside
{word_min}-{word_max}, revise before outputting."""

RESCRIPT_TEMPLATE = """Your previous attempt at this concept failed validation: {reason}

Fix only that issue and rewrite the script + shot list for this single concept, following
the same rules as before ({word_min}-{word_max} words, anchor_spoken included verbatim,
shot_list narration_segments reconstruct script exactly).

Concept:
```json
{concept_json}
```

Output a single JSON object, no commentary, no markdown fences:
{{"id":"{concept_id}","script":"","word_count":0,"pattern_used":"","mood":"","hook_overlay":"",
  "shot_list":[{{"index":0,"narration_segment":"","media_type":"stock|ai",
                "stock_query":"","visual_prompt":""}}]}}"""


def load_style_md() -> str:
    return STYLE_MD_PATH.read_text(encoding="utf-8")


def _concept_for_prompt(c: dict) -> dict:
    return {
        "id": c["id"], "title": c["title"], "hook": c["hook"], "spine": c["spine"],
        "anchor": c["anchor"], "anchor_spoken": c["anchor_spoken"],
        "mechanism": c["mechanism"], "consequence": c["consequence"],
        "pattern": c["pattern"], "confidence": c["confidence"],
    }


def _extract_json(raw_text: str):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"[\[{].*[\]}]", raw_text, re.DOTALL)
        if not match:
            raise ValueError(f"Could not find JSON in response. First 300 chars: {raw_text[:300]!r}")
        return json.loads(match.group(0))


def reconstruct_shots(shot_list: list[dict]) -> str:
    return " ".join(s.get("narration_segment", "") for s in shot_list)


def reconstruct_beats(beats: dict) -> str:
    return " ".join(beats.get(name, "").strip() for name in BEAT_ORDER).strip()


def estimated_seconds(script: str) -> float:
    return len(script.split()) / WORDS_PER_SECOND


def check_traps(script: str) -> list[str]:
    """Phrases that have hidden real errors before. Warnings, not failures -
    each is fine in some contexts and wrong in others, so a human decides."""
    return [
        f"{note} -> {match.group(0)!r}"
        for pattern, note in TRAP_PATTERNS
        if (match := re.search(pattern, script, re.I))
    ]


def validate_script(concept: dict, item: dict, prev_format: str | None = None) -> None:
    """Raises ValueError with a specific reason - never silently coerces.
    Every check maps to a real failure mode this project has already hit:
    drifted numbers, desynced shots, a one-word thumbnail, a script that ran
    long, a sidereal/solar day conflation that shipped as a false statement."""
    script = item.get("script", "")
    words = len(script.split())
    seconds = estimated_seconds(script)
    if not (RUNTIME_MIN_SECONDS <= seconds <= RUNTIME_MAX_SECONDS):
        raise ValueError(
            f"{words} words is about {seconds:.0f}s spoken, outside the "
            f"{RUNTIME_MIN_SECONDS:.0f}-{RUNTIME_MAX_SECONDS:.0f}s range"
        )
    if re.search(r"\d", script):
        raise ValueError("digit found in narration (numbers must be spelled out)")
    low = script.lower()
    for phrase in BANNED_PHRASES:
        if phrase in low:
            raise ValueError(f"banned phrase found: {phrase!r}")

    # --- five beats, and they must add up to exactly what gets spoken ---
    beats = item.get("beats") or {}
    missing = [b for b in BEAT_ORDER if not (beats.get(b) or "").strip()]
    if missing:
        raise ValueError(f"missing or empty beat(s): {', '.join(missing)}")
    if reconstruct_beats(beats) != script.strip():
        raise ValueError("the five beats do not concatenate to the narration exactly")

    # --- the hook is the payoff, not a run-up ---
    hook = beats["hook"].strip()
    hook_words = len(hook.split())
    if hook_words > HOOK_MAX_WORDS:
        raise ValueError(f"HOOK is {hook_words} words; must be under {HOOK_MAX_WORDS}")
    hook_low = hook.lower()
    for opener in BANNED_OPENERS:
        if hook_low.startswith(opener):
            raise ValueError(f"HOOK starts with a banned opener: {opener!r}")

    # --- format rotation, enforced rather than trusted ---
    fmt = (item.get("format_letter") or "").strip().upper()
    if fmt not in FORMAT_LETTERS:
        raise ValueError(f"format_letter {fmt!r} must be one of {sorted(FORMAT_LETTERS)}")
    if prev_format and fmt == prev_format.upper():
        raise ValueError(
            f"format {fmt} repeats the previous script's format - consecutive repeats "
            f"are what make a channel look machine-made"
        )

    # --- the viewer has to be in the script, especially at the end ---
    if len(SECOND_PERSON_RE.findall(script)) < MIN_SECOND_PERSON:
        raise ValueError(f"second person appears fewer than {MIN_SECOND_PERSON} times")
    if not SECOND_PERSON_RE.search(beats["loop"]):
        raise ValueError("the LOOP beat must address the viewer directly")

    for closer in BANNED_CLOSERS:
        if closer in low:
            raise ValueError(f"banned closer found: {closer!r}")

    if not (item.get("sources") or []):
        raise ValueError("missing sources block")

    title = (item.get("title") or concept.get("title") or "").strip()
    if len(title) > TITLE_MAX_CHARS:
        raise ValueError(f"title is {len(title)} chars; max {TITLE_MAX_CHARS}")
    if concept["anchor_spoken"].lower() not in low:
        raise ValueError(f"anchor_spoken {concept['anchor_spoken']!r} not found verbatim")
    # The overlay is half the "thumbnail" on a Short, so it gets checked like
    # one: a single word (the old "phone" failure) can never be a hook.
    overlay = (item.get("hook_overlay") or "").strip()
    if not overlay:
        raise ValueError("missing hook_overlay (the on-screen thumbnail text)")
    overlay_words = overlay.split()
    if not (2 <= len(overlay_words) <= 6):
        raise ValueError(
            f"hook_overlay is {len(overlay_words)} word(s) ({overlay!r}); must be 2-6 "
            f"words that name the subject and open a curiosity gap"
        )

    shot_list = item.get("shot_list") or []
    if not shot_list:
        raise ValueError("empty shot_list")
    if reconstruct_shots(shot_list) != script:
        raise ValueError("shot_list narration_segments do not reconstruct script exactly")
    for shot in shot_list:
        if shot.get("media_type") not in ("stock", "ai"):
            raise ValueError(f"shot {shot.get('index')}: bad media_type {shot.get('media_type')!r}")
        if not shot.get("visual_prompt"):
            raise ValueError(f"shot {shot.get('index')}: missing visual_prompt")
        if shot["media_type"] == "stock" and not shot.get("stock_query"):
            raise ValueError(f"shot {shot.get('index')}: stock shot missing stock_query")


def _call_batch(client: Anthropic, llm_cfg: dict, style_md: str, prompt: str, usage: LLMUsage) -> list[dict]:
    """Non-agentic: no tools, one request, one response. Style.md is cached -
    full price the first time this session, ~10% on reuse."""
    response = client.messages.create(
        model=llm_cfg["model"],
        max_tokens=llm_cfg.get("max_tokens", 6000),
        system=[{"type": "text", "text": style_md, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )
    usage.add_response(response)
    ceiling = llm_cfg.get("max_cost_per_scripting_batch_usd")
    if ceiling and usage.cost_usd(llm_cfg) > ceiling:
        raise RuntimeError(
            f"Scripting batch hit the ${ceiling:.2f} cost ceiling "
            f"(${usage.cost_usd(llm_cfg):.3f}); aborting."
        )
    if response.stop_reason == "max_tokens":
        raise RetryableError("Scripting batch response hit max_tokens and was truncated")
    texts = [b.text for b in response.content if b.type == "text" and b.text.strip()]
    if not texts:
        raise RetryableError("Scripting batch response contained no text")
    return _extract_json(texts[-1].strip())


def rescript_one(client: Anthropic, llm_cfg: dict, style_md: str, concept: dict, failure_reason: str, usage: LLMUsage) -> dict:
    prompt = RESCRIPT_TEMPLATE.format(
        reason=failure_reason,
        word_min=WORD_COUNT_MIN, word_max=WORD_COUNT_MAX,
        concept_json=json.dumps(_concept_for_prompt(concept)),
        concept_id=concept["id"],
    )

    def _call() -> dict:
        response = client.messages.create(
            model=llm_cfg["model"],
            max_tokens=llm_cfg.get("max_tokens", 6000),
            system=[{"type": "text", "text": style_md, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        usage.add_response(response)
        if response.stop_reason == "max_tokens":
            raise RetryableError("Rescript response hit max_tokens")
        texts = [b.text for b in response.content if b.type == "text" and b.text.strip()]
        if not texts:
            raise RetryableError("Rescript response contained no text")
        return _extract_json(texts[-1].strip())

    return retry_call(_call, description=f"Rescript {concept['id']}", attempts=2)


def _safe_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return (slug or "untitled")[:60]


def templatize(concept: dict, item: dict, config: dict) -> dict:
    """Deterministic, code-only construction of everything docs/prompt_scripting.md's
    'not the model's job' table assigns to Python - no LLM call for any of this."""
    title = _enforce_title_length(concept["title"])
    tags = keywords.normalize_tags(CLUSTER_TAGS.get(concept["cluster"], []) + BASE_TAGS)
    hashtags = " ".join(f"#{t.replace(' ', '')}" for t in dict.fromkeys(["Shorts"] + tags))
    description = f"{title}. {concept['consequence']}\n\n{hashtags}"
    # Deliberately written per script, NOT sliced from the hook. Slicing the
    # first four words produced fragments like "PHONE" - see style.md, "The
    # opening frame IS the thumbnail". validate_script() enforces the shape.
    hook_overlay = item["hook_overlay"].strip().upper()
    mood = _validate_mood(item.get("mood"), config["content"]["moods"])

    return {
        "id": concept["id"], "cluster": concept["cluster"], "pattern": item.get("pattern_used", concept["pattern"]),
        "topic": _safe_slug(title), "title": title, "description": description,
        "tags": tags, "hook_overlay": hook_overlay, "mood": mood,
        "script": item["script"], "shot_list": item["shot_list"],
        # Optional: written during the monthly session for videos we may want
        # a Hindi audio track on later (see scripts/make_hindi_audio.py).
        "script_hi": item.get("script_hi"),
        "central_claim": concept["mechanism"], "sources": [concept["source"]],
        "anchor": concept["anchor"], "anchor_spoken": concept["anchor_spoken"],
        "batch_id": datetime.now(timezone.utc).date().isoformat(),
        "status": "queued", "video_id": None,
        "queued_at": datetime.now(timezone.utc).isoformat(), "published_at": None,
    }


def generate_for_approved(config: dict, ledger: dict, max_items: int | None = None) -> list[dict]:
    idea_bank = load_idea_bank()
    approved = [c for c in idea_bank if c.get("status") == "approved"]
    batch_size = max_items or config["content"]["scripting"]["batch_size"]
    batch = approved[:batch_size]
    if not batch:
        print("[gen_scripts] No approved concepts in the idea bank. Nothing to do.")
        return []

    llm_cfg = config["providers"]["llm_scripting"]
    style_md = load_style_md()
    client = Anthropic(api_key=cfg.env("ANTHROPIC_API_KEY"))
    usage = LLMUsage()

    prompt = USER_PROMPT_TEMPLATE.format(
        n=len(batch),
        concepts_json=json.dumps([_concept_for_prompt(c) for c in batch]),
        moods=", ".join(config["content"]["moods"]),
        word_min=WORD_COUNT_MIN, word_max=WORD_COUNT_MAX,
    )

    try:
        raw_items = retry_call(
            lambda: _call_batch(client, llm_cfg, style_md, prompt, usage),
            description="Claude scripting batch", attempts=2,
        )
    except Exception as e:
        cost = usage.cost_usd(llm_cfg)
        budget.record_spend(
            ledger, "llm_scripting", cost,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
            cache_creation_tokens=usage.cache_creation_tokens, cache_read_tokens=usage.cache_read_tokens,
        )
        print(f"[gen_scripts] Batch call failed after ${cost:.3f} real spend: {e}", file=sys.stderr)
        raise

    items_by_id = {item.get("id"): item for item in raw_items if isinstance(item, dict)}
    per_item_retries = config["content"]["scripting"]["per_item_retry_attempts"]

    queued: list[dict] = []
    still_approved: list[dict] = []
    for concept in batch:
        item = items_by_id.get(concept["id"])
        reason = None
        if item is None:
            reason = "missing from batch response"
        else:
            try:
                validate_script(concept, item)
            except ValueError as e:
                reason = str(e)

        for attempt in range(per_item_retries):
            if reason is None:
                break
            print(f"[gen_scripts] {concept['id']} failed ({reason}); retrying "
                  f"individually (attempt {attempt + 1}/{per_item_retries}).", file=sys.stderr)
            try:
                item = rescript_one(client, llm_cfg, style_md, concept, reason, usage)
                validate_script(concept, item)
                reason = None
            except Exception as e:
                reason = str(e)
                item = None

        if reason is not None:
            print(f"[gen_scripts] {concept['id']} still failing after retries ({reason}); "
                  f"leaving it 'approved' for next run.", file=sys.stderr)
            still_approved.append(concept)
            continue

        queued_item = templatize(concept, item, config)
        queued.append(queued_item)
        concept["status"] = "scripted"
        concept["scripted_at"] = datetime.now(timezone.utc).isoformat()

    cost = usage.cost_usd(llm_cfg)
    budget.record_spend(
        ledger, "llm_scripting", cost,
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        cache_creation_tokens=usage.cache_creation_tokens, cache_read_tokens=usage.cache_read_tokens,
    )
    print(
        f"[gen_scripts] {len(queued)}/{len(batch)} concepts scripted and queued. "
        f"{len(still_approved)} left approved (unresolved after retries). "
        f"Real cost: ${cost:.3f} ({usage.input_tokens} in / {usage.output_tokens} out tokens, "
        f"cache read: {usage.cache_read_tokens})."
    )

    if queued:
        append_script_queue(queued)
    save_idea_bank(idea_bank)  # persists status='scripted' mutations made in place above
    return queued


def ingest_file(config: dict, path: str) -> list[dict]:
    """Loads hand-written scripts (a JSON array) into the ready-to-publish queue.

    No Anthropic client is constructed anywhere in this path - free by
    construction, not by estimate. Every item still goes through the exact
    same validate_script() the API path uses, so hand-written work cannot skip
    a check the generated work had to pass. Anything that fails is reported
    and skipped rather than silently queued; fix it and re-run.
    """
    cfg.ensure_dirs()
    idea_bank = load_idea_bank()
    by_id = {c["id"]: c for c in idea_bank}

    items = _extract_json(Path(path).read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = [items]
    print(f"[gen_scripts] Parsed {len(items)} script(s) from {path}.")

    queued, failed = [], []
    for item in items:
        concept = by_id.get(item.get("id"))
        if concept is None:
            failed.append((item.get("id"), "no matching concept in the idea bank"))
            continue
        try:
            validate_script(concept, item)
        except ValueError as e:
            failed.append((item.get("id"), str(e)))
            continue
        queued.append(templatize(concept, item, config))
        concept["status"] = "scripted"
        concept["scripted_at"] = datetime.now(timezone.utc).isoformat()

    if queued:
        append_script_queue(queued)
        save_idea_bank(idea_bank)

    print(f"[gen_scripts] {len(queued)} script(s) queued, {len(failed)} rejected.")
    for item_id, reason in failed:
        print(f"  rejected: {item_id} - {reason}", file=sys.stderr)
    return queued


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ingest", metavar="PATH",
        help="Load hand-written scripts (JSON array) instead of calling the API. Free.",
    )
    args = parser.parse_args()

    config = cfg.load_config()
    cfg.ensure_dirs()

    if args.ingest:
        ingest_file(config, args.ingest)
        return

    ledger = budget.load_ledger()
    try:
        generate_for_approved(config, ledger)
    finally:
        budget.save_ledger(ledger)


if __name__ == "__main__":
    main()
