"""Uploads the finished MP4 to YouTube as a Short using a stored OAuth refresh
token (see scripts/get_refresh_token.py for the one-time setup flow)."""
from __future__ import annotations

from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from . import config as cfg

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
# Note: admin.yml's videos.update (changing visibility on an already-published video)
# needs the broader "https://www.googleapis.com/auth/youtube" scope, which the current
# refresh token does NOT have. Requesting a wider scope than a token was originally
# granted makes the refresh call itself fail (invalid_scope), breaking uploads too - so
# don't widen SCOPES here without also regenerating YOUTUBE_REFRESH_TOKEN to match
# (rerun scripts/get_refresh_token.py after updating SCOPES, then update the GitHub secret).
TOKEN_URI = "https://oauth2.googleapis.com/token"


def credentials() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=cfg.env("YOUTUBE_REFRESH_TOKEN"),
        token_uri=TOKEN_URI,
        client_id=cfg.env("YOUTUBE_CLIENT_ID"),
        client_secret=cfg.env("YOUTUBE_CLIENT_SECRET"),
        scopes=SCOPES,
    )


def youtube_client():
    return build("youtube", "v3", credentials=credentials())


def upload_short(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    visibility: str = "unlisted",
) -> str:
    """Uploads video_path and returns the resulting videoId."""
    if "#shorts" not in description.lower() and "#shorts" not in title.lower():
        description = f"{description}\n\n#Shorts"

    youtube = youtube_client()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": visibility,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]
