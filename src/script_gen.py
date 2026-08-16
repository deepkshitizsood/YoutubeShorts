"""Generates the day's script + metadata + shot list via Claude Haiku."""
from __future__ import annotations

import json
import random
import re
import sys

from anthropic import Anthropic

from . import config as cfg
from .http_util import RetryableError, retry_call

SYSTEM_PROMPT = """You write scripts for a daily YouTube Shorts channel about surprising facts.
You must return ONLY valid JSON matching the schema given in the user message - no prose,
no markdown fences.

What matters, in order:
1. The viewer decides whether to swipe away within the first second. The opening
   line must land a concrete, surprising claim immediately - never a preamble,
   never "have you ever wondered".
2. Watch-through rate decides how far the video spreads. Every sentence must earn
   the next one. No filler, no restating, no wind-down before the payoff.
3. Rewatches are a powerful ranking signal, so the last line should loop back to
   the opening idea, making the video feel seamless if it replays."""

USER_PROMPT_TEMPLATE = """Content pillar: {pillar_description}
Hook style required: {hook_style}
Call to action: {cta}
Topics already covered recently (do NOT repeat these, pick something clearly distinct
in subject matter, not just a different slug): {recent_topics}
Avoid entirely: {avoid_topics}

Target narration length for THIS video: {word_target} words (~{target_seconds} seconds).

Write one new YouTube Short. Return JSON with exactly this schema:
{{
  "topic": "short slug describing the topic, e.g. 'octopus_three_hearts'",
  "title": "YouTube title, <=60 chars, curiosity-driven, include relevant emoji sparingly",
  "description": "1-3 sentences summarizing the hook/payoff, then a blank line, then
    7-10 hashtags for reach: always include #Shorts and #facts, plus a mix of broad
    discovery tags (e.g. #didyouknow, #mindblowing, #factsdaily, #wow) and 3-5 tags
    specific to this video's exact topic/subject",
  "tags": ["array", "of", "8-12", "seo", "tags", "mixing", "broad", "and", "topic-specific", "terms"],
  "hook": "the first spoken sentence, <=8 words, a punchy standalone claim or question",
  "hook_overlay": "3-6 words in ALL CAPS shown on screen from the very first frame,
    capturing the hook visually for viewers who watch muted",
  "script": "the FULL narration script (hook included), {word_target} words, spoken conversationally",
  "shot_list": [
    {{"index": 0,
      "narration_segment": "the exact words from `script` that this shot covers, verbatim",
      "media_type": "stock" or "ai",
      "stock_query": "1-3 plain search words for stock footage, e.g. 'octopus swimming'
        (REQUIRED when media_type is 'stock', omit otherwise)",
      "visual_prompt": "detailed text-to-image prompt, vertical composition, cinematic
        (REQUIRED always - it is the fallback when no stock footage matches)"}},
    ...
  ]
}}

Shot pacing: produce {shot_count} shots, each covering only ~2-3 seconds of narration.
Fast cuts hold attention; long static shots lose it. The narration_segment fields,
concatenated in order with a single space between each, must reconstruct `script`
EXACTLY (same words, same order, nothing skipped or duplicated) - this drives visual timing.

media_type rules:
- Use "stock" for concrete, filmable subjects that real footage exists for: animals,
  landscapes, weather, space, everyday objects, city scenes, food, human hands/crowds.
  Give a simple, literal stock_query - stock libraries match plain nouns, not prose.
- Use "ai" for abstract, historical, microscopic, hypothetical or otherwise unfilmable
  ideas, and for anything needing a specific invented composition.
- Prefer "stock" when either would work: real motion outperforms a static image.

visual_prompt entries must NOT depict real/identifiable people; use illustrative,
abstract, nature, object, or generic-figure imagery instead.
"""


def _pick_length_variant(config: dict) -> dict:
    """Chooses this run's target length from the configured variants.

    Lengths are deliberately varied so the analytics loop can learn which
    performs better on this specific channel, rather than assuming the
    published benchmarks transfer.
    """
    variants = config["content"]["length_variants"]
    weights = [v.get("weight", 1) for v in variants]
    return random.choices(variants, weights=weights, k=1)[0]


def generate_script(config: dict, strategy_brief: dict) -> dict:
    client = Anthropic(api_key=cfg.env("ANTHROPIC_API_KEY"))
    content_cfg = config["content"]
    variant = _pick_length_variant(config)
    prompt = USER_PROMPT_TEMPLATE.format(
        pillar_description=strategy_brief["pillar_description"],
        hook_style=content_cfg["hook_style"],
        cta=content_cfg["cta"],
        recent_topics=", ".join(strategy_brief["recent_topics_to_avoid"]) or "none yet",
        avoid_topics=", ".join(content_cfg["avoid_topics"]),
        word_target=variant["words"],
        target_seconds=variant["seconds"],
        shot_count=variant["shots"],
    )

    def _call() -> str:
        response = client.messages.create(
            model=config["providers"]["llm"]["model"],
            max_tokens=4000,  # a 9-shot list with verbose visual_prompts runs close to 2k
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        # A truncated response yields unparseable JSON; retrying is worth a shot
        # since the model may produce a more compact shot list next time.
        if response.stop_reason == "max_tokens":
            raise RetryableError("Claude response hit max_tokens and was truncated")
        return response.content[0].text.strip()

    raw_text = retry_call(_call, description="Claude script generation")
    data = _parse_json_response(raw_text)

    required_keys = {"topic", "title", "description", "tags", "hook", "script", "shot_list"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"LLM output missing keys: {missing}")

    if not data.get("shot_list"):
        raise ValueError("LLM returned an empty shot_list")

    _fixup_shot_word_counts(data)
    data["length_variant"] = variant["name"]
    return data


def generate_unique_script(config: dict, strategy_brief: dict, used_topics: set[str]) -> dict:
    """Generates a script whose topic hasn't been used before.

    The prompt already lists recent topics to avoid, but nothing enforced it -
    at 3 posts/day the prompt's recent-topics window covers only a few days, so
    collisions are checked explicitly and regenerated.
    """
    attempts = 3
    for attempt in range(1, attempts + 1):
        data = generate_script(config, strategy_brief)
        topic = data["topic"].strip().lower()
        if topic not in used_topics:
            return data
        print(
            f"[script] Topic {topic!r} already used (attempt {attempt}/{attempts}); regenerating.",
            file=sys.stderr,
        )
    print(f"[script] Proceeding with repeated topic {data['topic']!r} after {attempts} attempts.", file=sys.stderr)
    return data


def _parse_json_response(raw_text: str) -> dict:
    """Claude Haiku reliably returns bare JSON when instructed to, but this is an
    unattended daily job - fall back to extracting the first {...} block (e.g. if
    it wraps the JSON in a markdown fence) rather than crashing the whole run."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass  # fall through to the combined error below
        raise ValueError(
            f"Could not parse JSON from Claude response ({e}). "
            f"First 300 chars: {raw_text[:300]!r}"
        ) from e


def _fixup_shot_word_counts(data: dict) -> None:
    """Rescales shot word-counts to exactly cover the script's word count if the
    LLM's narration_segment split drifted slightly, so downstream timing never
    goes out of bounds. Mutates data['shot_list'] in place, adding 'word_count'."""
    total_words = len(data["script"].split())
    shots = data["shot_list"]
    raw_counts = [max(len(s["narration_segment"].split()), 1) for s in shots]
    raw_total = sum(raw_counts)
    scaled = [max(round(c * total_words / raw_total), 1) for c in raw_counts]
    # Correct rounding drift on the last shot so counts sum exactly to total_words.
    scaled[-1] += total_words - sum(scaled)
    scaled[-1] = max(scaled[-1], 1)
    for shot, count in zip(shots, scaled):
        shot["word_count"] = count
