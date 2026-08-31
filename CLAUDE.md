# Project rules for Claude Code

This repo documents its own rationale in code comments and config.yaml —
read those instead of re-deriving architecture here. This file is only for
rules that aren't obvious from the code itself.

## Money — hard rules, not preferences
- Never raise `budget.monthly_cap_usd`, `providers.llm.max_cost_per_script_usd`,
  or `posting.videos_per_day` without stating the $ impact and getting
  explicit approval in the same message — not just noting it in the commit.
- Never weaken or bypass the `budget.status()` cap check.
- `--dry-run` skips the YouTube upload only — script, TTS, and image calls
  are still billed in full. Don't run more dry-run tests than the task needs.
- Before adding any new paid API/service, state its per-unit cost and get
  approval first.

## Strategy/config changes need sign-off, even when data-backed
- Changes to `content.niche`, `content.pillars`, `content.audience`, or any
  `providers.*.model` are strategic decisions. Propose the change and the
  evidence; don't commit it unasked.

## Secrets
- Never print, log, or commit anything from `.env` or any API key. Flag any
  hardcoded credential found in code as a bug — don't fix it silently.

## Keep your own footprint small
- Don't read `assets/music`, `assets/sfx`, or other binary/asset folders
  unless the task specifically concerns audio or assembly.
- Use targeted file reads/greps, not a full-repo scan, unless explicitly
  asked to audit everything.
- Prefer small, targeted diffs over rewriting whole files.
- Keep commit messages short; put reasoning in code comments, matching this
  repo's existing style.

## Docs
- README.md must match config.yaml's actual current state (model, posting
  cadence, cost estimate). If a change makes them disagree, update both in
  the same commit.