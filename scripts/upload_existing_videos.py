"""One-off admin script: upload pre-rendered video files that already sit in
output/_manual_upload/ (bypassing script/TTS/image generation entirely).

Used once to publish 3 videos that were already generated during pipeline
testing, to the correct channel, without spending anything on regeneration.
"""
from __future__ import annotations

from src import config as cfg
from src import upload

VIDEOS = [
    {
        "path": "output/_manual_upload/bananas_radioactive.mp4",
        "title": "Your Bananas Are Radioactive \U0001F34C☢️",
        "description": (
            "Yes, really - bananas contain enough potassium-40 to register on a "
            "Geiger counter. You'd need to eat about 10 million at once for it to "
            "actually matter, but the radiation is technically there. \U0001F34C⚡\n\n"
            "#Shorts #facts #didyouknow #mindblowing #factsdaily #wow #science "
            "#bananas #radioactive #funfacts"
        ),
        "tags": ["facts", "didyouknow", "mindblowing", "science", "radioactive",
                  "potassium", "funfacts", "shorts", "nature", "biology"],
    },
    {
        "path": "output/_manual_upload/mantis_shrimp_color_vision.mp4",
        "title": "Mantis Shrimp Sees Colors You Can't \U0001F990",
        "description": (
            "Mantis shrimp have up to 16 color receptors - we only have 3 - and can "
            "see wavelengths of light that are completely invisible to the human "
            "eye. Nature's most overpowered vision system. \U0001F990\U0001F441️\n\n"
            "#Shorts #facts #didyouknow #mindblowing #factsdaily #wow #ocean "
            "#mantisshrimp #animalfacts #nature"
        ),
        "tags": ["facts", "didyouknow", "mindblowing", "ocean life", "animal facts",
                  "nature", "mantis shrimp", "marine biology", "shorts", "wildlife"],
    },
    {
        "path": "output/_manual_upload/woodpeckers_skull_shock_absorption.mp4",
        "title": "Why Woodpeckers Don't Get Concussions \U0001FAB5",
        "description": (
            "Woodpeckers slam their heads into trees up to 20 times per second and "
            "never get a concussion - their skulls have a built-in shock absorber "
            "humans could only dream of. \U0001FAB5\U0001F9E0\n\n"
            "#Shorts #facts #didyouknow #mindblowing #factsdaily #wow #birds "
            "#woodpecker #animalfacts #nature"
        ),
        "tags": ["facts", "didyouknow", "mindblowing", "animal facts", "nature",
                  "woodpecker", "birds", "biology", "shorts", "wildlife"],
    },
]


def main() -> None:
    config = cfg.load_config()
    upload.verify_channel(config["channel"]["handle"])
    print(f"[upload] Verified target channel: {config['channel']['handle']}")

    for v in VIDEOS:
        video_id = upload.upload_short(
            video_path=cfg.REPO_ROOT / v["path"],
            title=v["title"],
            description=v["description"],
            tags=v["tags"],
            visibility=config["posting"]["visibility_on_launch"],
        )
        print(f"Published {v['path']} -> video_id={video_id}")


if __name__ == "__main__":
    main()
