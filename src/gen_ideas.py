"""Call A - ideation. Generates a batch of concept ideas via Claude Sonnet 5 +
web_search, auto-filters them, and appends survivors to data/idea_bank.jsonl
for human review (see scripts/approve_ideas.py).

Run manually / via .github/workflows/ideation_batch.yml:
    python -m src.gen_ideas [--n 40]

See docs/prompt_ideation.md for the prompt this implements, and the plan
(lets-build-an-agent-resilient-clock.md, Section 1) for the design rationale.

Search-economy note: web_search's max_uses is a hard, API-enforced cap on
searches for the WHOLE batch, not per-concept - the real reason this matters
is that the current per-video pipeline measures 155K-304K input tokens per
call from search-result ingestion alone. A naive "verify every concept"
policy here would multiply that across 40 concepts instead of amortizing it,
which is the entire point of moving verification off the daily path.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from anthropic import Anthropic

from . import config as cfg
from . import budget, strategy
from .http_util import RetryableError, retry_call
from .script_gen import LLMUsage, ScriptGenerationFailed, _count_searches, _final_text

# Kept in sync with style.md's hook pattern list by hand - both files describe
# the same fixed vocabulary, one for generating concepts, one for varying scripts.
HOOK_PATTERNS = [
    "INVERTED_ASSUMPTION", "NAKED_NUMBER", "SECOND_PERSON_IMPLICATION",
    "SCALE_COLLAPSE", "TIMEBOMB", "MISSING_THING", "WRONG_NAME", "OBSERVER_LIMIT",
]
MIN_PATTERN_USES = 3

SYSTEM_PROMPT_TEMPLATE = """You are a concept scout for {niche}, a YouTube Shorts channel. Your job
is to find facts that stop a scroll - not to write scripts.

A good concept has all four of these. A concept missing any one of them is not a concept:

1. A gap. It contradicts something a curious non-expert currently believes, or answers a
   question they didn't know was open.
2. An anchor number. One specific, verifiable figure with a unit. Not "very far" -
   "one hundred and sixty thousand light years".
3. A mechanism. The *why* behind the fact, explainable in one sentence without equations.
   Facts with no mechanism are trivia and die at low retention.
4. A consequence. Something that changes because this is true - for the viewer, for the
   subject, or for what we can ever know.

Reject anything unfalsifiable, or a fact whose only interest is its size, or something
already ubiquitous in this niche's short-form content.

You have web search, but it is a SHARED budget across this entire batch of {n} concepts,
not one search per concept - see the search budget instructions in the user message.
Do not generate a concept you could not source, but do not attempt to verify every
concept individually; the budget will run out long before the last one.

Your FINAL message must be ONLY the JSONL output specified in the user message - one
JSON object per line, no wrapper array, no prose, no markdown fences. Searching and
reasoning happen before that."""

USER_PROMPT_TEMPLATE = """Generate {n} concepts for {niche}.

Exclusions - do not propose anything covering the same core fact as these already-used
titles (the last 60 published/dry-run videos):
{exclusions}

SEARCH BUDGET: you have a shared budget of {search_budget} searches for this entire batch
of {n} concepts - roughly one search per {n_per_search} concepts. Do not attempt to verify
every concept individually; that budget will run out long before the last one. Instead:
- Rely on well-established facts you are already confident of without spending a search.
- When several candidate concepts share a topic, mission, or instrument, cover them with
  ONE broader search rather than one each.
- Spend a search only on a number that is likely to have changed recently, that you are
  genuinely unsure of, or that is central enough that being wrong would sink the concept.
- For anything you mark confidence "leading_theory" or "contested", do not search at all -
  search cannot resolve a genuine disagreement; say so honestly in `confidence` instead.
- If you exhaust the budget, keep going without further searches rather than stalling.

Distribution requirement. Spread the {n} across these subject clusters, no more than
{max_per_cluster} from any one:
{clusters}

Hook pattern requirement. Assign each concept one pattern from this list, and use each
pattern at least {min_pattern_uses} times across the batch:
{patterns}

For each concept, write two competing hook lines (hook_a, hook_b) - they are cheap and the
gate picks the winner. They must take different angles on the same fact, not be rewordings
of each other.

Output one JSON object per line, no wrapper array, no commentary before or after. Do NOT
include an `id` field - ids are assigned afterward in code:

{{"title":"","hook_a":"","hook_b":"","spine":"","anchor":"","anchor_spoken":"","mechanism":"","consequence":"","cluster":"","pattern":"","source":"","confidence":"confirmed|leading_theory|contested","saturation":"low|medium|high"}}

Field rules:
- title: the YouTube title, under 60 characters, no clickbait punctuation.
- hook_a / hook_b: spoken first line, under 12 words each.
- spine: the whole video in one sentence. If you can't, the concept is too big.
- anchor: the number and its unit, alone, in digit/notation form, e.g. "93 billion light years".
- anchor_spoken: the same number, spelled out exactly the way it must be spoken in
  narration, e.g. "ninety three billion light years" - never digits.
- mechanism: one sentence, no equations, plain English.
- consequence: what changes because this is true.
- source: a URL you actually retrieved, or a named mission/paper/instrument.
- saturation: your honest read on how often this already appears in this niche's
  short-form content. Anything you mark "high" will be filtered out - mark it honestly.

Return exactly {n} lines. Nothing else."""


def _run_ideation_call(client: Anthropic, llm_cfg: dict, system: str, prompt: str, usage: LLMUsage):
    """Ideation's own small resume loop - deliberately not shared with
    script_gen.py's _run_with_search: the ceiling here is whole-batch
    (max_cost_per_ideation_batch_usd), not per-script, and duplicating this
    ~15-line loop is cheaper than risking the live daily path to share it.
    """
    tools = [{
        "type": llm_cfg.get("search_tool_type", "web_search_20260209"),
        "name": "web_search",
        "max_uses": llm_cfg["search_budget_per_batch"],
    }]
    messages = [{"role": "user", "content": prompt}]
    ceiling = llm_cfg.get("max_cost_per_ideation_batch_usd")
    max_continuations = 2

    for _ in range(max_continuations):
        response = client.messages.create(
            model=llm_cfg["model"],
            max_tokens=llm_cfg.get("max_tokens", 12000),
            system=system,
            tools=tools,
            messages=messages,
        )
        usage.add_response(response)
        if ceiling and usage.cost_usd(llm_cfg) > ceiling:
            raise RuntimeError(
                f"Ideation batch hit the ${ceiling:.2f} whole-batch cost ceiling "
                f"(${usage.cost_usd(llm_cfg):.3f} across {usage.calls} call(s)); "
                f"aborting rather than retrying or continuing further."
            )
        if response.stop_reason != "pause_turn":
            return response
        messages = messages[:1] + [{"role": "assistant", "content": response.content}]

    raise RetryableError(f"Ideation search loop still paused after {max_continuations} continuations")


def _parse_jsonl_response(raw_text: str, expected_n: int) -> list[dict]:
    """Parses one-JSON-object-per-line output. A malformed line is dropped
    and logged, not fatal to the whole batch - the batch already paid for
    every line, so losing 39 good concepts over 1 bad line would be wasteful."""
    concepts = []
    for i, line in enumerate(raw_text.strip().splitlines()):
        line = line.strip().rstrip(",")
        if not line:
            continue
        try:
            concepts.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"[gen_ideas] Line {i + 1} failed to parse ({e}); dropping it. Raw: {line[:200]!r}",
                  file=sys.stderr)
    if not concepts:
        raise ValueError(f"No valid JSONL lines parsed from response. First 300 chars: {raw_text[:300]!r}")
    if len(concepts) < expected_n:
        print(
            f"[gen_ideas] Expected {expected_n} concepts, parsed {len(concepts)} - "
            f"continuing with what parsed.",
            file=sys.stderr,
        )
    return concepts


def generate_ideas(config: dict, exclusion_titles: list[str], n: int | None = None) -> tuple[list[dict], LLMUsage]:
    """One Call-A request for the whole batch. Returns (raw_concepts, usage) -
    raw_concepts have no id/status/batch_id yet; run_batch() adds those."""
    ideation_cfg = config["content"]["ideation"]
    n = n or ideation_cfg["batch_size"]
    clusters = ideation_cfg["clusters"]
    max_per_cluster = max(4, (n // len(clusters)) + 2)
    search_budget = ideation_cfg["search_budget_per_batch"]

    system = SYSTEM_PROMPT_TEMPLATE.format(niche=config["content"]["niche"], n=n)
    prompt = USER_PROMPT_TEMPLATE.format(
        n=n,
        niche=config["content"]["niche"],
        exclusions="\n".join(f"- {t}" for t in exclusion_titles) or "(none yet)",
        search_budget=search_budget,
        n_per_search=max(1, n // search_budget),
        max_per_cluster=max_per_cluster,
        clusters=", ".join(clusters),
        min_pattern_uses=MIN_PATTERN_USES,
        patterns=", ".join(HOOK_PATTERNS),
    )

    llm_cfg = dict(config["providers"]["llm_ideation"])
    llm_cfg["search_budget_per_batch"] = search_budget
    client = Anthropic(api_key=cfg.env("ANTHROPIC_API_KEY"))
    usage = LLMUsage()

    def _call() -> tuple[str, int]:
        response = _run_ideation_call(client, llm_cfg, system, prompt, usage)
        if response.stop_reason == "max_tokens":
            raise RetryableError("Ideation response hit max_tokens and was truncated")
        return _final_text(response), _count_searches(response)

    try:
        raw_text, searches = retry_call(_call, description="Claude ideation batch", attempts=2)
    except Exception as e:
        raise ScriptGenerationFailed(e, usage, llm_cfg) from e

    concepts = _parse_jsonl_response(raw_text, n)
    return concepts, usage


def auto_filter(concepts: list[dict], recent_clusters: set[str]) -> list[dict]:
    """Code-only gate per docs/prompt_ideation.md: keeps concepts with real
    sourcing and non-saturated topics. Rejects are kept (status='rejected'),
    not deleted, for audit trail - only the human gate step (approve_ideas.py)
    should be the last word on what actually gets scripted."""
    for c in concepts:
        keep = (
            c.get("saturation") != "high"
            and bool(c.get("anchor"))
            and bool(c.get("source"))
            and c.get("cluster") not in recent_clusters
        )
        c["status"] = "pending_review" if keep else "rejected"
    return concepts


def _next_id(existing: list[dict]) -> int:
    max_num = 0
    for e in existing:
        eid = e.get("id", "")
        if eid.startswith("cb-"):
            try:
                max_num = max(max_num, int(eid[3:]))
            except ValueError:
                pass
    return max_num + 1


def load_idea_bank() -> list[dict]:
    if not cfg.IDEA_BANK_PATH.exists():
        return []
    ideas = []
    with open(cfg.IDEA_BANK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ideas.append(json.loads(line))
    return ideas


def save_idea_bank(ideas: list[dict]) -> None:
    with open(cfg.IDEA_BANK_PATH, "w", encoding="utf-8") as f:
        for idea in ideas:
            f.write(json.dumps(idea) + "\n")


def append_idea_bank(new_concepts: list[dict]) -> list[dict]:
    existing = load_idea_bank()
    next_num = _next_id(existing)
    for i, c in enumerate(new_concepts):
        c["id"] = f"cb-{next_num + i:04d}"
    existing.extend(new_concepts)
    save_idea_bank(existing)
    return new_concepts


def run_batch(config: dict, ledger: dict, n: int | None = None) -> list[dict]:
    """Full Call-A flow: exclusions -> generate -> filter -> append to the
    idea bank -> record real spend (success or failure)."""
    cfg.ensure_dirs()
    history = strategy.load_content_history()
    exclusion_titles = strategy.recent_titles(history, limit=60)

    try:
        concepts, usage = generate_ideas(config, exclusion_titles, n=n)
    except ScriptGenerationFailed as e:
        budget.record_spend(
            ledger, "llm_ideation", e.cost_usd,
            input_tokens=e.input_tokens, output_tokens=e.output_tokens,
            searches=e.searches,
            cache_creation_tokens=e.cache_creation_tokens, cache_read_tokens=e.cache_read_tokens,
        )
        print(
            f"[gen_ideas] Failed after ${e.cost_usd:.3f} real spend "
            f"({e.input_tokens} in / {e.output_tokens} out tokens, {e.searches} search(es)) "
            f"- see traceback below.",
            file=sys.stderr,
        )
        raise

    llm_cfg = config["providers"]["llm_ideation"]
    cost = usage.cost_usd(llm_cfg)
    budget.record_spend(
        ledger, "llm_ideation", cost,
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        searches=usage.searches,
        cache_creation_tokens=usage.cache_creation_tokens, cache_read_tokens=usage.cache_read_tokens,
    )
    print(
        f"[gen_ideas] Generated {len(concepts)} concepts. Real cost: ${cost:.3f} "
        f"({usage.input_tokens} in / {usage.output_tokens} out tokens, {usage.searches} search(es))."
    )

    recent_clusters = {h.get("cluster") for h in history[-6:] if h.get("cluster")}
    filtered = auto_filter(concepts, recent_clusters)
    for c in filtered:
        c.setdefault("hook", None)
        c["batch_id"] = datetime.now(timezone.utc).date().isoformat()
        c["created_at"] = datetime.now(timezone.utc).isoformat()
        c["reviewed_at"] = None
        c["scripted_at"] = None

    saved = append_idea_bank(filtered)
    kept = sum(1 for c in saved if c["status"] == "pending_review")
    print(f"[gen_ideas] {kept}/{len(saved)} concepts passed the auto-filter and await review "
          f"(python -m scripts.approve_ideas).")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=None, help="Number of concepts to generate")
    args = parser.parse_args()

    config = cfg.load_config()
    ledger = budget.load_ledger()
    try:
        run_batch(config, ledger, n=args.n)
    finally:
        budget.save_ledger(ledger)


if __name__ == "__main__":
    main()
