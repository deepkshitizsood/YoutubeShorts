"""Weekly performance review, written to stdout as Markdown.

Deliberately conservative about claims: with a handful of videos, most
differences between pillars/lengths/moods are noise, so every comparison is
reported with its sample size and is explicitly labelled as not-yet-meaningful
below a threshold. A report that says "too early to tell" is more useful than a
confident wrong steer.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from src import config as cfg
from src.strategy import score_video

# Below this many videos in a bucket, differences are treated as noise.
MIN_SAMPLE = 4
# Retention that triggers wide algorithmic distribution.
STRONG_RETENTION = 70.0
# Expanded-tier monetization bar.
TIER_VIEWS, TIER_SUBS, TIER_DAYS = 3_000_000, 500, 90
# 25 videos of generic "any surprising fact" content topped out at 1,373 views,
# with 65% mean retention - good content, capped reach. The whole point of the
# niche pivot is whether videos ever clear this again.
CEILING_VIEWS = 1_400
# When the space-niche pivot shipped - videos published before this are the old
# unbounded-topic baseline; on/after are the pivot.
NICHE_PIVOT_DATE = "2026-08-27"


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _joined() -> list[dict]:
    perf = {e["video_id"]: e for e in _load(cfg.PERFORMANCE_LOG_PATH) if e.get("video_id")}
    rows = []
    for h in _load(cfg.CONTENT_HISTORY_PATH):
        vid = h.get("video_id")
        if not vid or h.get("dry_run") or vid not in perf:
            continue
        rows.append({**h, **perf[vid]})
    return rows


def _bucket(rows, key) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in rows:
        if r.get(key):
            out[r[key]].append(r)
    return out


def _compare(rows, key, label, lines):
    buckets = _bucket(rows, key)
    if not buckets:
        lines.append(f"**{label}:** no data yet.\n")
        return
    lines.append(f"**{label}**\n")
    lines.append("| " + label + " | videos | mean retention | mean views |")
    lines.append("|---|---:|---:|---:|")
    for name, items in sorted(buckets.items(), key=lambda kv: -_mean(kv[1], "average_view_percentage")):
        lines.append(
            f"| {name} | {len(items)} | {_mean(items, 'average_view_percentage'):.0f}% "
            f"| {_mean(items, 'views'):.0f} |"
        )
    biggest = max(len(v) for v in buckets.values())
    if biggest < MIN_SAMPLE:
        lines.append(
            f"\n> Not yet meaningful - largest group has {biggest} video(s), "
            f"below the {MIN_SAMPLE} needed before a difference is worth acting on.\n"
        )
    else:
        lines.append("")


def _mean(items, field) -> float:
    vals = [i.get(field, 0) or 0 for i in items]
    return sum(vals) / len(vals) if vals else 0.0


def main() -> None:
    config = cfg.load_config()
    rows = _joined()
    today = datetime.now(timezone.utc).date()
    L = [f"# Factodixs weekly report - {today}", ""]

    if not rows:
        L.append(
            "No videos with analytics yet. YouTube's reporting lag is ~72h, so "
            "very recent uploads will not appear."
        )
        print("\n".join(L))
        return

    total_views = sum(r.get("views", 0) for r in rows)
    mean_ret = _mean(rows, "average_view_percentage")
    best = max(rows, key=lambda r: r.get("views", 0))
    worst = min(rows, key=lambda r: r.get("views", 0))
    best_ret = max(rows, key=lambda r: r.get("average_view_percentage", 0))
    max_views = best.get("views", 0)
    over_ceiling = [r for r in rows if r.get("views", 0) > CEILING_VIEWS]

    # --- headline -------------------------------------------------------
    L += [
        "## Headline", "",
        f"- **{len(rows)} videos** with analytics, **{total_views:,} total views**",
        f"- Mean retention **{mean_ret:.0f}%** "
        f"({'above' if mean_ret >= STRONG_RETENTION else 'below'} the ~{STRONG_RETENTION:.0f}% "
        f"that triggers wide distribution)",
        f"- Most views: **{best.get('title', best['video_id'])}** - {best.get('views', 0):,} views, "
        f"{best.get('average_view_percentage', 0):.0f}% retention",
        f"- Best retention: **{best_ret.get('title', best_ret['video_id'])}** - "
        f"{best_ret.get('average_view_percentage', 0):.0f}%, {best_ret.get('views', 0):,} views",
        f"- Fewest views: **{worst.get('title', worst['video_id'])}** - {worst.get('views', 0):,} views",
        "",
        f"**Ceiling check: {'BROKEN' if over_ceiling else 'still capped'}** - "
        f"max views is {max_views:,}, {len(over_ceiling)}/{len(rows)} video(s) above "
        f"{CEILING_VIEWS:,}. Every prior video topped out under that line despite good "
        f"retention, which is why the niche pivot happened - this is the number that "
        f"says whether it worked, not retention.",
        "",
    ]

    # --- monetization ---------------------------------------------------
    pct = total_views / TIER_VIEWS * 100
    L += [
        "## Against the monetization bar", "",
        f"Expanded tier needs **{TIER_SUBS} subs + {TIER_VIEWS:,} Shorts views/{TIER_DAYS} days**.",
        f"Lifetime views so far: **{total_views:,}** ({pct:.2f}% of the view bar).",
        "",
    ]
    if rows:
        per_day = total_views / max((len(rows) / config["posting"]["videos_per_day"]), 1)
        L.append(
            f"At the current rate (~{per_day:,.0f} views/day) that is "
            f"~{per_day * TIER_DAYS:,.0f} views per 90 days - "
            f"{'on track' if per_day * TIER_DAYS >= TIER_VIEWS else 'short of the bar, so retention and volume both need to rise'}."
        )
        L.append("")

    # --- breakdowns -----------------------------------------------------
    L.append("## Breakdowns")
    L.append("")
    for key, label in (
        ("pillar_id", "Pillar"), ("series_id", "Series"),
        ("length_variant", "Length"), ("mood", "Mood"),
    ):
        _compare(rows, key, label, L)

    # --- before/after the niche pivot ------------------------------------
    before = [r for r in rows if r.get("created_at", "") < NICHE_PIVOT_DATE]
    after = [r for r in rows if r.get("created_at", "") >= NICHE_PIVOT_DATE]
    L.append(f"**Before vs after the {NICHE_PIVOT_DATE} niche pivot**\n")
    if not after:
        L.append(
            "> No post-pivot videos have cleared the ~72h analytics lag yet - "
            "too early to compare.\n"
        )
    else:
        L.append("| | videos | mean views | max views | mean retention | comment rate |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for name, items in (("Before (unbounded topics)", before), ("After (space niche)", after)):
            if not items:
                L.append(f"| {name} | 0 | - | - | - | - |")
                continue
            v = [i.get("views", 0) for i in items]
            comments = sum(i.get("comments", 0) for i in items)
            views_sum = sum(v) or 1
            L.append(
                f"| {name} | {len(items)} | {sum(v) / len(items):.0f} | {max(v)} | "
                f"{_mean(items, 'average_view_percentage'):.0f}% | "
                f"{100 * comments / views_sum:.2f}% |"
            )
        if len(after) < MIN_SAMPLE:
            L.append(
                f"\n> Only {len(after)} post-pivot video(s) so far, below the "
                f"{MIN_SAMPLE} needed to draw a conclusion - directional only.\n"
            )
        else:
            L.append("")

    # --- spend ----------------------------------------------------------
    ledger = _load(cfg.SPEND_LEDGER_PATH)
    prefix = f"{today.year:04d}-{today.month:02d}"
    mtd = sum(e["usd"] for e in ledger["entries"] if e["date"].startswith(prefix))
    cap = config["budget"]["monthly_cap_usd"]
    projected = mtd / max(today.day, 1) * 30
    L += [
        "## Spend", "",
        f"- Month to date: **${mtd:.2f}** of ${cap:.0f} cap",
        f"- Projected month end at current rate: **${projected:.2f}**"
        + ("  ⚠️ over cap" if projected > cap else ""),
        "",
    ]

    # --- anomalies ------------------------------------------------------
    L.append("## Anomalies")
    L.append("")
    flagged = False
    for r in rows:
        if r.get("views", 0) <= 2:
            L.append(
                f"- **{r.get('title', r['video_id'])}** got {r.get('views', 0)} views - "
                f"check whether it reached the Shorts feed at all."
            )
            flagged = True
    unverified = [r for r in rows if not r.get("web_searches")]
    if unverified:
        L.append(
            f"- **{len(unverified)} video(s) written with no web search** - their claims "
            f"were never verified, which is what caused the earlier accuracy complaints."
        )
        flagged = True
    if not flagged:
        L.append("- None.")
    L.append("")

    print("\n".join(L))


if __name__ == "__main__":
    main()
