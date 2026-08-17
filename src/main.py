"""Orchestrates one full daily run: analytics pull -> strategy -> script ->
voiceover -> visuals -> assembly -> upload -> ledger/history update.

Usage:
    python src/main.py             # full run, uploads to YouTube
    python src/main.py --dry-run   # generates the video locally, skips upload
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from . import config as cfg
from . import budget, strategy, script_gen, tts, visuals, assemble, upload, analytics


def _safe_slug(topic: str) -> str:
    """Makes an LLM-supplied topic safe to use as a directory name."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", topic).strip("_")
    return (slug or "untitled")[:60]


def run(dry_run: bool) -> None:
    cfg.ensure_dirs()
    config = cfg.load_config()
    ledger = budget.load_ledger()
    # Spend is recorded into `ledger` as each paid API call happens, but only
    # persisted here in `finally` - otherwise a crash in visuals/assembly/upload
    # discards money already spent and the monthly cap never sees it.
    try:
        _run_pipeline(dry_run, config, ledger)
    finally:
        budget.save_ledger(ledger)
        print(f"[budget] Month-to-date spend: ${budget.month_to_date_spend(ledger):.2f}")


def _run_pipeline(dry_run: bool, config: dict, ledger: dict) -> None:
    status = budget.status(ledger, config)
    if status == "over":
        print(f"[budget] Monthly cap of ${config['budget']['monthly_cap_usd']} reached. Skipping run.")
        return
    if status == "warn":
        print(f"[budget] Warning: month-to-date spend is above ${config['budget']['warn_threshold_usd']}.")

    upload.verify_channel(config["channel"]["handle"])
    print(f"[upload] Verified target channel: {config['channel']['handle']}")

    try:
        new_entries = analytics.pull_and_log()
        print(f"[analytics] Logged {len(new_entries)} fresh performance snapshot(s).")
    except Exception as e:  # analytics failures shouldn't block content production
        print(f"[analytics] Skipped (not fatal): {e}", file=sys.stderr)

    brief = strategy.build_strategy_brief(config)
    print(f"[strategy] Pillar: {brief['pillar_id']} (exploration={brief['is_exploration']})")
    strategy.print_learning_report()

    used_topics = strategy.used_topics()
    data = script_gen.generate_unique_script(config, brief, used_topics)
    print(
        f"[script] Topic: {data['topic']} | Length: {data.get('length_variant', '?')} "
        f"| Title: {data['title']}"
    )
    print(
        f"[verify] {data.get('web_searches', 0)} web search(es), "
        f"{len(data.get('sources') or [])} source(s) | claim: {data.get('central_claim', 'n/a')}"
    )
    if not data.get("web_searches"):
        print(
            "[verify] WARNING: script was written with no web search - claims are "
            "unverified.",
            file=sys.stderr,
        )
    budget.record_spend(ledger, "llm_script", config["providers"]["llm"]["est_cost_per_script_usd"])

    run_folder_name = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + _safe_slug(data["topic"])
    run_dir = cfg.OUTPUT_DIR / run_folder_name
    tmp_dir = run_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    narration = tts.synthesize(config, data["script"])
    narration_path = run_dir / "narration.wav"
    narration_path.write_bytes(narration.audio_bytes)
    tts_cost = tts.estimated_cost_usd(config, narration.char_count)
    budget.record_spend(ledger, "tts", tts_cost)
    print(f"[tts] {len(narration.word_timings)} words synthesized (~${tts_cost:.3f})")

    media_dir = run_dir / "media"
    shot_media_paths, shot_kinds, billable_images = visuals.resolve_shot_media(
        config, data["shot_list"], media_dir
    )
    # Stock clips are free and reused images are already paid for, so only newly
    # generated images are billed.
    image_cost = visuals.estimated_image_cost_usd(config, billable_images)
    budget.record_spend(ledger, "images", image_cost)
    print(f"[visuals] Image spend ~${image_cost:.3f}")

    final_path = run_dir / "final.mp4"
    assemble.assemble_video(
        config=config,
        shot_list=data["shot_list"],
        shot_media_paths=shot_media_paths,
        shot_kinds=shot_kinds,
        narration_wav_path=narration_path,
        word_timings=narration.word_timings,
        tmp_dir=tmp_dir,
        out_path=final_path,
        hook_overlay=data.get("hook_overlay"),
        mood=data.get("mood"),
    )
    print(f"[assemble] Final video: {final_path}")

    video_id = None
    try:
        if not dry_run:
            video_id = upload.upload_short(
                video_path=final_path,
                title=data["title"],
                description=data["description"],
                tags=data["tags"],
                visibility=config["posting"]["visibility_on_launch"],
            )
            print(f"[upload] Published as video_id={video_id}")
        else:
            print("[upload] Skipped (--dry-run)")
    finally:
        # Recorded even if the upload throws: if the insert actually landed
        # before erroring, tomorrow's run must still know this topic is used,
        # or it regenerates the same one and double-posts it.
        strategy.append_content_history({
            "topic": data["topic"],
            "pillar_id": brief["pillar_id"],
            "title": data["title"],
            "video_id": video_id,
            "length_variant": data.get("length_variant"),
            "mood": data.get("mood"),
            # Audit trail: if a viewer disputes a claim, this is what was checked.
            "central_claim": data.get("central_claim"),
            "sources": data.get("sources"),
            "web_searches": data.get("web_searches"),
            "stock_shots": sum(1 for k in shot_kinds if k == "video"),
            "total_shots": len(shot_kinds),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
        })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate the video but skip upload")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
