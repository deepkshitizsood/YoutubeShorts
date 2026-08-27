"""Daily spend breakdown across every paid API in the pipeline, written to
stdout as Markdown - filed as a GitHub issue once a day so real spend is
visible without opening data/spend_ledger.json by hand. Real per-video cost
used to be invisible: the ledger logged a flat estimate for LLM calls
regardless of what Anthropic actually billed, which is how the account ran
out of credits without any report ever showing it coming.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src import budget
from src import config as cfg

DAYS_SHOWN = 7


def main() -> None:
    config = cfg.load_config()
    ledger = budget.load_ledger()
    today = datetime.now(timezone.utc).date()
    cap = config["budget"]["monthly_cap_usd"]

    by_day_item: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    items: set[str] = set()
    for e in ledger["entries"]:
        day = e["date"][:10]
        by_day_item[day][e["item"]] += e["usd"]
        items.add(e["item"])
    sorted_items = sorted(items)

    mtd = budget.month_to_date_spend(ledger, today)
    run_status = budget.status(ledger, config)

    L = [f"# Daily spend report - {today}", ""]
    L.append(f"**Month to date: ${mtd:.2f} of ${cap:.0f} cap** (status: {run_status})")
    if run_status == "over":
        L.append(
            "\n> The monthly cap has been reached - main.py's pre-flight check "
            "refuses further runs until next month (or a config change)."
        )
    elif run_status == "warn":
        L.append(f"\n> Above the ${config['budget']['warn_threshold_usd']:.0f} warning threshold.")
    L.append("")

    if not sorted_items:
        L.append("No spend recorded yet.")
        print("\n".join(L))
        return

    days = [today - timedelta(days=i) for i in range(DAYS_SHOWN)]
    L.append("| Date | " + " | ".join(sorted_items) + " | Total |")
    L.append("|---|" + "---:|" * (len(sorted_items) + 1))
    for d in days:
        row = by_day_item.get(d.isoformat(), {})
        total = sum(row.values())
        cells = " | ".join(f"${row.get(i, 0):.3f}" if row.get(i) else "-" for i in sorted_items)
        L.append(f"| {d.isoformat()} | {cells} | ${total:.3f} |")
    L.append("")

    projected = mtd / max(today.day, 1) * 30
    L.append(
        f"Projected month-end at the current daily rate: **${projected:.2f}**"
        + ("  ⚠️ over cap" if projected > cap else "")
    )

    print("\n".join(L))


if __name__ == "__main__":
    main()
