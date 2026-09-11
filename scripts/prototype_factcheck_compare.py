"""One-off decision tool: compares Claude Sonnet 5 + web_search against Gemini
2.5 Flash + Google Search grounding on a fixed set of test claims, to decide
which provider gen_ideas.py's search-verification step should call.

Not part of the production pipeline - run once, manually:
    python -m scripts.prototype_factcheck_compare

Real spend: ~$0.10-$0.50 total (a handful of small calls on each side). Get
explicit go-ahead before running, per this project's rule on real API spend.

Why this exists (plan Section 0): Gemini's per-token rate is ~6x cheaper than
Claude's, but that assumes similar search-result token ingestion volume,
which is unverified - and cost isn't the only axis. The whole reason search
verification exists on this channel is a real prior accuracy incident, so a
cheaper-but-worse verifier is not a win. Read both sides' output by hand
before trusting the cost number alone.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests
from anthropic import Anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config as cfg
from src.http_util import raise_for_retryable_status, retry_call
from src.script_gen import LLMUsage, _count_searches, _final_text, _run_with_search

# Spans confidence levels the way real ideation concepts will: a precise
# number worth checking, a textbook fact, a classic myth, and one genuinely
# contested/leading-theory claim search can't actually resolve.
TEST_CLAIMS = [
    "The exact current distance from Earth to Voyager 1 in miles, as of now.",
    "Whether the Great Wall of China is visible from space with the naked eye.",
    "The confirmed number of moons Saturn has as of the most recent official count.",
    "The surface temperature of Venus at its hottest, in Celsius.",
    "Whether black holes 'suck in' everything nearby, or only what crosses the event horizon.",
    "The leading theory for what dark matter is made of - phrased honestly as unresolved.",
    "How long it takes light from the Sun to reach Earth, precisely.",
    "Whether the 'dark side of the Moon' is actually always dark.",
]

OUTPUT_SCHEMA_INSTRUCTIONS = """For each claim, research it and return a JSON array, one object per
claim, in the same order, with exactly these fields:
{"claim": "...", "verified_answer": "the true answer in one sentence",
 "anchor": "the key number/fact alone, or null if the claim has none",
 "anchor_spoken": "the number spelled out as spoken words, or null",
 "confidence": "confirmed" | "leading_theory" | "contested",
 "source": "a real URL or named source you actually found, or null"}
Return ONLY the JSON array - no prose, no markdown fences."""

CLAUDE_LLM_CFG = {
    "model": "claude-sonnet-5",
    "max_tokens": 12000,
    "search_tool_type": "web_search_20260209",
    "max_searches_per_script": 8,
    "pricing_usd_per_million_tokens": {"input": 2.0, "output": 10.0},
    "web_search_cost_per_use_usd": 0.01,
    # Safety net for this small test, not a real per-script ceiling. Raised
    # alongside max_tokens - the first attempt at 4000/$1.00 hit max_tokens
    # before finishing, so both were sized too tight for 8 claims + sources.
    "max_cost_per_script_usd": 2.00,
}

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
# Verified 2026-09-11 against https://ai.google.dev/gemini-api/docs/pricing.
# Grounding tool fee (1,500 free requests/day, then $35/1000) is assumed $0
# here - this prototype's volume is nowhere near the free-tier limit.
GEMINI_PRICING = {"input": 0.30, "output": 2.50}


def _prompt() -> str:
    claims = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(TEST_CLAIMS))
    return f"Verify these {len(TEST_CLAIMS)} claims:\n{claims}\n\n{OUTPUT_SCHEMA_INSTRUCTIONS}"


def _extract_json_array(raw_text: str) -> list[dict]:
    """Lenient parse: falls back to the first [...] block if wrapped in prose
    or a markdown fence - either provider may not obey "no prose" perfectly."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if not match:
            raise ValueError(
                f"Could not find a JSON array in response. First 300 chars: {raw_text[:300]!r}"
            )
        return json.loads(match.group(0))


def verify_with_claude() -> tuple[list[dict], LLMUsage]:
    client = Anthropic(api_key=cfg.env("ANTHROPIC_API_KEY"))
    usage = LLMUsage()
    system = "You are a careful fact-checker. Use the web_search tool to verify each claim before answering."
    response = _run_with_search(client, CLAUDE_LLM_CFG, system, _prompt(), usage)
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude response hit max_tokens - reduce TEST_CLAIMS or raise max_tokens")
    results = _extract_json_array(_final_text(response))
    return results, usage


def verify_with_gemini(api_key: str) -> tuple[list[dict], dict]:
    """Uses the same generateContent REST endpoint already proven working in
    this repo (visuals.py's image generation), with a Google Search grounding
    tool added. The exact grounding tool shape has some real documentation
    uncertainty as of this writing - if this 400s, the error body below will
    show what Google's API actually expects; that's a legitimate, cheap
    outcome of a prototype, not a bug to silently work around."""
    system_and_prompt = (
        "You are a careful fact-checker. Use Google Search to verify each claim before answering.\n\n"
        + _prompt()
    )
    payload = {
        "contents": [{"parts": [{"text": system_and_prompt}]}],
        "tools": [{"google_search": {}}],
    }

    def _call() -> dict:
        resp = requests.post(
            GEMINI_ENDPOINT, headers={"x-goog-api-key": api_key}, json=payload, timeout=90
        )
        raise_for_retryable_status(resp, "Gemini generateContent (grounding prototype)")
        return resp.json()

    body = retry_call(_call, description="Gemini fact-check grounding call")

    candidates = body.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates. Response: {str(body)[:500]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if "text" in p)
    if not text.strip():
        raise RuntimeError(f"Gemini returned no text content. Response: {str(body)[:500]}")

    results = _extract_json_array(text)
    usage_meta = body.get("usageMetadata", {})
    usage = {
        "input_tokens": usage_meta.get("promptTokenCount", 0),
        "output_tokens": usage_meta.get("candidatesTokenCount", 0),
    }
    return results, usage


def gemini_cost_usd(usage: dict) -> float:
    return (
        usage["input_tokens"] * GEMINI_PRICING["input"] / 1_000_000
        + usage["output_tokens"] * GEMINI_PRICING["output"] / 1_000_000
    )


def _print_side(label: str, results: list[dict]) -> None:
    print(f"\n=== {label} ===")
    for r in results:
        print(f"- {r.get('claim', '?')[:70]}")
        print(f"    answer: {r.get('verified_answer')}")
        print(f"    anchor: {r.get('anchor')} / spoken: {r.get('anchor_spoken')}")
        print(f"    confidence: {r.get('confidence')}  source: {r.get('source')}")


def main() -> None:
    # Tried first per the plan: AI Studio keys typically cover the whole
    # Gemini API surface, not just the image model this key was created for.
    google_key = cfg.env("GOOGLE_IMAGE_API_KEY")

    print(f"Testing {len(TEST_CLAIMS)} claims against Claude Sonnet 5 + web_search...")
    claude_results, claude_usage = verify_with_claude()
    claude_cost = claude_usage.cost_usd(CLAUDE_LLM_CFG)

    print(f"Testing {len(TEST_CLAIMS)} claims against Gemini 2.5 Flash + Google Search grounding...")
    gemini_results, gemini_usage = verify_with_gemini(google_key)
    gcost = gemini_cost_usd(gemini_usage)

    _print_side("Claude Sonnet 5 + web_search", claude_results)
    _print_side("Gemini 2.5 Flash + Google Search grounding", gemini_results)

    print("\n=== Cost comparison ===")
    print(
        f"Claude: ${claude_cost:.4f}  "
        f"({claude_usage.input_tokens} in / {claude_usage.output_tokens} out tokens, "
        f"{claude_usage.searches} search(es))"
    )
    print(
        f"Gemini: ${gcost:.4f}  "
        f"({gemini_usage['input_tokens']} in / {gemini_usage['output_tokens']} out tokens; "
        f"grounding fee assumed $0 at this volume - verify in AI Studio usage if unsure)"
    )
    if gcost > 0:
        print(f"Claude is {claude_cost / gcost:.1f}x the cost of Gemini for this test batch.")
    print(
        "\nNow read both sides above and judge accuracy/source quality by hand - "
        "the cheaper answer is not the better one if it's wrong or unsourced."
    )


if __name__ == "__main__":
    main()
