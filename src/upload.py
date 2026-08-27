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


def verify_channel(expected_handle: str) -> None:
    """Confirms the authenticated token's channel matches config.yaml's channel.handle
    before we spend any money or upload anything - guards against a repeat of uploading
    to the wrong channel (e.g. a Google account's personal channel instead of the
    intended Brand Account channel) if the refresh token ever gets regenerated wrong."""
    youtube = youtube_client()
    resp = youtube.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError("No channel found for the authenticated account.")

    actual_handle = items[0]["snippet"].get("customUrl", "")
    actual_title = items[0]["snippet"].get("title", "")
    expected = expected_handle.lstrip("@").lower()
    actual = actual_handle.lstrip("@").lower()
    if expected != actual:
        raise RuntimeError(
            f"Authenticated channel is '{actual_title}' ({actual_handle}), but "
            f"config.yaml expects '{expected_handle}'. Refusing to upload - this usually "
            f"means the OAuth refresh token is bound to the wrong channel/brand account. "
            f"Regenerate it with scripts/get_refresh_token.py, picking the correct channel "
            f"at the account-chooser step."
        )


# 28 = Science & Technology. Was 24 (Entertainment), which mis-signalled a space
# channel to YouTube's classifier and to the audience clusters we want to land in.
CATEGORY_SCIENCE_AND_TECH = "28"


def upload_short(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    visibility: str = "unlisted",
    category_id: str = CATEGORY_SCIENCE_AND_TECH,
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
            "categoryId": category_id,
            # Declaring the language helps YouTube route the video to the right
            # audience and enables auto-caption/translation paths.
            "defaultLanguage": "en-US",
            "defaultAudioLanguage": "en-US",
        },
        "status": {
            "privacyStatus": visibility,
            "selfDeclaredMadeForKids": False,
            # Compliance, not optimization: every video is AI-generated imagery
            # plus synthetic narration, and YouTube requires that be disclosed.
            # Undisclosed synthetic media puts monetization standing at risk -
            # the exact thing this channel is working toward.
            "containsSyntheticMedia": True,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]
