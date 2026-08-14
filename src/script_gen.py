"""Generates the day's script + metadata + shot list via Claude Haiku."""
from __future__ import annotations

import json
import re

from anthropic import Anthropic

from . import config as cfg

SYSTEM_PROMPT = """You write scripts for a daily YouTube Shorts channel about surprising facts.
You must return ONLY valid JSON matching the schema given in the user message - no prose,
no markdown fences. Every video must be a self-contained 45-55 second narration."""

USER_PROMPT_TEMPLATE = """Content pillar: {pillar_description}
Hook style required: {hook_style}
Call to action: {cta}
Topics already covered recently (do NOT repeat these, pick something distinct): {recent_topics}
Avoid entirely: {avoid_topics}

Write one new YouTube Short. Return JSON with exactly this schema:
{{
  "topic": "short slug describing the topic, e.g. 'octopus_three_hearts'",
  "title": "YouTube title, <=60 chars, curiosity-driven, include relevant emoji sparingly",
  "description": "1-3 sentences + 3-5 relevant hashtags including #Shorts",
  "tags": ["array", "of", "5-8", "seo", "tags"],
  "hook": "the first 1-2 spoken sentences, must grab attention immediately",
  "script": "the FULL narration script (hook included), 130-160 words, spoken conversationally",
  "shot_list": [
    {{"index": 0,
      "narration_segment": "the exact words from `script` that this shot covers, verbatim",
      "visual_prompt": "detailed text-to-image prompt for this beat, vertical composition, cinematic"}},
    ...
  ]
}}
Produce 6-9 shots in shot_list, each covering ~6-8 seconds of narration, in the order they're spoken about.
The narration_segment fields, concatenated in order with a space between each, must reconstruct `script`
exactly (same words, same order, nothing skipped or duplicated) - this is used to time the visuals.
visual_prompt entries must NOT depict real/identifiable people; use illustrative, abstract, nature, object,
or generic-figure imagery instead.
"""


def generate_script(config: dict, strategy_brief: dict) -> dict:
    client = Anthropic(api_key=cfg.env("ANTHROPIC_API_KEY"))
    content_cfg = config["content"]
    prompt = USER_PROMPT_TEMPLATE.format(
        pillar_description=strategy_brief["pillar_description"],
        hook_style=content_cfg["hook_style"],
        cta=content_cfg["cta"],
        recent_topics=", ".join(strategy_brief["recent_topics_to_avoid"]) or "none yet",
        avoid_topics=", ".join(content_cfg["avoid_topics"]),
    )

    response = client.messages.create(
        model=config["providers"]["llm"]["model"],
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.content[0].text.strip()
    data = _parse_json_response(raw_text)

    required_keys = {"topic", "title", "description", "tags", "hook", "script", "shot_list"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"LLM output missing keys: {missing}")

    _fixup_shot_word_counts(data)
    return data


def _parse_json_response(raw_text: str) -> dict:
    """Claude Haiku reliably returns bare JSON when instructed to, but this is an
    unattended daily job - fall back to extracting the first {...} block (e.g. if
    it wraps the JSON in a markdown fence) rather than crashing the whole run."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


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
