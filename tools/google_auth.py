"""Shared Google OAuth credential loading, for Gmail + Drive access.

Two modes:
  - Local/interactive (default): reads credentials.json/token.json from the project root,
    runs the browser consent flow if needed. Used when developing/testing on this machine.
  - Headless (Trigger.dev): if GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN
    are all set as env vars, builds credentials directly from them - no browser, no local
    files. Trigger.dev's Python extension auto-injects its configured secrets into os.environ.

Scopes: gmail.send + drive (the subscriber sheet already exists and wasn't created by this
OAuth client, so drive.file alone isn't enough - drive is needed for read access to it, plus
write access to create newsletter files). If you're re-running the local consent flow after
this scope changed, delete token.json first so a stale, narrower-scoped token isn't reused.
"""
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_PATH = Path("credentials.json")
TOKEN_PATH = Path("token.json")


def get_credentials(scopes: list = None) -> Credentials:
    scopes = scopes or SCOPES

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")
    if client_id and client_secret and refresh_token:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
        )
        creds.refresh(Request())
        return creds

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                sys.exit(
                    "Missing credentials.json in the project root. See the setup "
                    "instructions at the top of tools/send_newsletter.py."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), scopes)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds
