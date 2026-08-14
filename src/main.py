"""Orchestrates one full daily run: analytics pull -> strategy -> script ->
voiceover -> visuals -> assembly -> upload -> ledger/history update.

Usage:
    python src/main.py             # full run, uploads to YouTube
    python src/main.py --dry-run   # generates the video locally, skips upload
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from . import config as cfg
from . import budget, strategy, script_gen, tts, visuals, assemble, upload, analytics


def run(dry_run: bool) -> None:
    cfg.ensure_dirs()
    config = cfg.load_config()
    ledger = budget.load_ledger()

    status = budget.status(ledger, config)
    if status == "over":
        print(f"[budget] Monthly cap of ${config['budget']['monthly_cap_usd']} reached. Skipping run.")
        return
    if status == "warn":
        print(f"[budget] Warning: month-to-date spend is above ${config['budget']['warn_threshold_usd']}.")

    try:
        new_entries = analytics.pull_and_log()
        print(f"[analytics] Logged {len(new_entries)} fresh performance snapshot(s).")
    except Exception as e:  # analytics failures shouldn't block content production
        print(f"[analytics] Skipped (not fatal): {e}", file=sys.stderr)

    brief = strategy.build_strategy_brief(config)
    print(f"[strategy] Pillar: {brief['pillar_id']} (exploration={brief['is_exploration']})")

    data = script_gen.generate_script(config, brief)
    print(f"[script] Topic: {data['topic']} | Title: {data['title']}")
    budget.record_spend(ledger, "llm_script", config["providers"]["llm"]["est_cost_per_script_usd"])

    run_folder_name = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + data["topic"]
    run_dir = cfg.OUTPUT_DIR / run_folder_name
    tmp_dir = run_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    narration = tts.synthesize(config, data["script"])
    narration_path = run_dir / "narration.wav"
    narration_path.write_bytes(narration.audio_bytes)
    tts_cost = tts.estimated_cost_usd(config, narration.char_count)
    budget.record_spend(ledger, "tts", tts_cost)
    print(f"[tts] {len(narration.word_timings)} words synthesized (~${tts_cost:.3f})")

    images_dir = run_dir / "images"
    shot_media_paths = visuals.generate_images_for_shots(config, data["shot_list"], images_dir)
    image_cost = visuals.estimated_image_cost_usd(config, len(shot_media_paths))
    budget.record_spend(ledger, "images", image_cost)
    print(f"[visuals] Generated {len(shot_media_paths)} images (~${image_cost:.3f})")

    hero_shot_index = None
    if budget.hero_clip_allowed(ledger, config):
        try:
            hero_path = run_dir / "hero_clip.mp4"
            visuals.generate_hero_clip(config, shot_media_paths[0], data["hook"], hero_path)
            shot_media_paths[0] = hero_path
            hero_shot_index = 0
            hero_cost = visuals.estimated_hero_clip_cost_usd(config)
            budget.record_spend(ledger, "hero_video_clip", hero_cost)
            print(f"[visuals] Hero clip generated (~${hero_cost:.3f})")
        except Exception as e:
            print(f"[visuals] Hero clip skipped (not fatal): {e}", file=sys.stderr)

    final_path = run_dir / "final.mp4"
    assemble.assemble_video(
        config=config,
        shot_list=data["shot_list"],
        shot_media_paths=shot_media_paths,
        hero_shot_index=hero_shot_index,
        narration_wav_path=narration_path,
        word_timings=narration.word_timings,
        tmp_dir=tmp_dir,
        out_path=final_path,
    )
    print(f"[assemble] Final video: {final_path}")

    video_id = None
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

    strategy.append_content_history({
        "topic": data["topic"],
        "pillar_id": brief["pillar_id"],
        "title": data["title"],
        "video_id": video_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
    })

    budget.save_ledger(ledger)
    print(f"[budget] Month-to-date spend: ${budget.month_to_date_spend(ledger):.2f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate the video but skip upload")
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
