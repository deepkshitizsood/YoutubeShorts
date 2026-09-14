"""Human gate for ideation output. Walks every 'pending_review' concept in
data/idea_bank.jsonl and lets you approve (picking the winning hook), reject,
or skip it. Nothing gets scripted until it passes this gate - see the plan
(lets-build-an-agent-resilient-clock.md, Section 1).

Run locally, interactively:
    python -m scripts.approve_ideas

Commit and push data/idea_bank.jsonl afterward so the scripting batch
(python -m src.gen_scripts, or its workflow) can see the approvals.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.gen_ideas import load_idea_bank, save_idea_bank  # noqa: E402


def _prompt_one(c: dict) -> None:
    print(f"\n{'=' * 70}")
    print(f"[{c['id']}] cluster={c['cluster']}  pattern={c['pattern']}  confidence={c['confidence']}")
    print(f"Title: {c['title']}")
    print(f"  (a) {c['hook_a']}")
    print(f"  (b) {c['hook_b']}")
    print(f"Spine: {c['spine']}")
    print(f"Anchor: {c['anchor']}  Source: {c['source']}")

    while True:
        choice = input("[a]pprove hook_a / [b]pprove hook_b / [r]eject / [s]kip > ").strip().lower()
        if choice in ("a", "b"):
            c["status"] = "approved"
            c["hook"] = c["hook_a"] if choice == "a" else c["hook_b"]
            c["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            print(f"Approved with hook_{choice}.")
            return
        if choice == "r":
            c["status"] = "rejected"
            c["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            print("Rejected.")
            return
        if choice == "s":
            print("Skipped - still pending_review.")
            return
        print("Type a, b, r, or s.")


def main() -> None:
    ideas = load_idea_bank()
    pending = [c for c in ideas if c.get("status") == "pending_review"]
    if not pending:
        print("No pending_review concepts in data/idea_bank.jsonl.")
        return

    print(f"{len(pending)} concept(s) awaiting review.")
    for c in pending:
        _prompt_one(c)

    save_idea_bank(ideas)
    approved = sum(1 for c in ideas if c["status"] == "approved")
    rejected = sum(1 for c in ideas if c["status"] == "rejected")
    still_pending = sum(1 for c in ideas if c["status"] == "pending_review")
    print(f"\nDone. approved={approved} rejected={rejected} still_pending={still_pending}")
    print("Commit and push data/idea_bank.jsonl so the scripting batch can see this.")


if __name__ == "__main__":
    main()
