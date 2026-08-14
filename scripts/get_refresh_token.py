"""One-time local script: run this yourself after creating the OAuth Client ID
in Google Cloud Console, to obtain a refresh token for the agent to use in CI.

Usage:
    python scripts/get_refresh_token.py --client-id XXX --client-secret YYY

Opens a browser, you log in as the YouTube channel's Google account and grant
access, then this prints the refresh token to store as the YOUTUBE_REFRESH_TOKEN
GitHub Actions secret. Never commit the printed token to the repo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.upload import SCOPES  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    args = parser.parse_args()

    client_config = {
        "installed": {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(port=0)

    print("\nSuccess. Store this as the YOUTUBE_REFRESH_TOKEN GitHub secret:\n")
    print(credentials.refresh_token)


if __name__ == "__main__":
    main()
