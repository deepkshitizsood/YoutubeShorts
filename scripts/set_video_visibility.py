"""Admin utility: change an already-uploaded video's privacy status.

Usage:
    python -m scripts.set_video_visibility --video-id XXXXXXXXXXX --visibility public
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.upload import youtube_client  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--visibility", required=True, choices=["public", "unlisted", "private"])
    args = parser.parse_args()

    youtube = youtube_client()
    youtube.videos().update(
        part="status",
        body={"id": args.video_id, "status": {"privacyStatus": args.visibility}},
    ).execute()
    print(f"video_id={args.video_id} set to {args.visibility}")


if __name__ == "__main__":
    main()
