#!/usr/bin/env python3
"""Send the Monk10x newsletter via the Gmail API, with real inline images.

Why this exists instead of the Gmail connector: the Gmail MCP connector's
send_message strips every <img> tag from the HTML body before sending -
confirmed by testing cid:, data:, and https: sources, all silently removed.
Building the raw MIME message ourselves is the only way to get inline images
into the email (see workflows/newsletter_automation.md, Step 6).

One-time setup (required before first use):
  1. Go to https://console.cloud.google.com/, create or select a project.
  2. Enable the Gmail API (APIs & Services > Library > Gmail API > Enable).
  3. Configure the OAuth consent screen (External is fine; add your Gmail
     account as a test user if it's in Testing mode).
  4. Also enable the Google Drive API (needed for tools/drive_client.py's scope).
  5. Create credentials: APIs & Services > Credentials > Create Credentials >
     OAuth client ID > Application type: Desktop app.
  6. Download the JSON and save it as credentials.json in the project root
     (gitignored already).
  7. Run this script once - it opens a browser for consent and caches the
     result as token.json (also gitignored). Later runs reuse it silently
     until the refresh token is revoked.

Credential loading is shared with tools/drive_client.py via tools/google_auth.py, which also
supports headless (Trigger.dev) auth from GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET/
GOOGLE_REFRESH_TOKEN env vars instead of local files - see that module's docstring.

Usage:
    python tools/send_newsletter.py \
        --html .tmp/newsletter_<slug>.html \
        --hero-image .tmp/images/<file>.png \
        [--support-image .tmp/images/<file>.png] \
        [--chart-image .tmp/images/chart-<slug>.png] \
        --to kislayranjan@gmail.com \
        --subject "Your subject line" \
        [--bcc a@x.com,b@y.com]

The logo (Brand Assets/monk_logo_transparent.png) is attached automatically.
The HTML must reference cid:monk10x_logo, cid:newsletter_hero_image, and optionally
cid:newsletter_support_image / cid:newsletter_chart_image (see tools/brand.py) - this
script wires those Content-IDs to the actual attached files.
"""
import argparse
import base64
import mimetypes
import sys
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.discovery import build as build_service

sys.path.insert(0, str(Path(__file__).parent))
import brand  # noqa: E402
import google_auth  # noqa: E402

LOGO_PATH = Path("Brand Assets/monk_logo_transparent.png")


def attach_inline_image(msg: MIMEMultipart, path: Path, content_id: str) -> None:
    if not path.exists():
        sys.exit(f"Image not found: {path}")
    mime_type, _ = mimetypes.guess_type(str(path))
    subtype = (mime_type or "image/png").split("/")[-1]
    with open(path, "rb") as f:
        img = MIMEImage(f.read(), _subtype=subtype)
    img.add_header("Content-ID", f"<{content_id}>")
    img.add_header("Content-Disposition", "inline", filename=path.name)
    msg.attach(img)


def build_message(to: list, bcc: list, subject: str, html_path: Path, images: dict) -> dict:
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["To"] = ", ".join(to)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

    html = html_path.read_text(encoding="utf-8")
    msg.attach(MIMEText(html, "html", "utf-8"))

    for cid, path in images.items():
        attach_inline_image(msg, Path(path), cid)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw}


def main():
    parser = argparse.ArgumentParser(description="Send a Monk10x newsletter issue via the Gmail API")
    parser.add_argument("--html", required=True, help="Path to the built newsletter HTML")
    parser.add_argument("--hero-image", required=True, help="Path to the issue's hero photo")
    parser.add_argument("--support-image", default=None, help="Optional second inline photo")
    parser.add_argument("--chart-image", default=None, help="Optional business-impact chart PNG")
    parser.add_argument("--to", required=True, help="Comma-separated To addresses")
    parser.add_argument("--bcc", default=None, help="Comma-separated Bcc addresses (use for subscriber blasts)")
    parser.add_argument("--subject", required=True)
    args = parser.parse_args()

    to = [a.strip() for a in args.to.split(",") if a.strip()]
    bcc = [a.strip() for a in args.bcc.split(",") if a.strip()] if args.bcc else []

    images = {brand.LOGO_CID: LOGO_PATH, brand.NEWSLETTER_HERO_CID: args.hero_image}
    if args.support_image:
        images[brand.NEWSLETTER_SUPPORT_CID] = args.support_image
    if args.chart_image:
        images[brand.NEWSLETTER_CHART_CID] = args.chart_image

    creds = google_auth.get_credentials()
    service = build_service("gmail", "v1", credentials=creds)

    message = build_message(to, bcc, args.subject, Path(args.html), images)
    sent = service.users().messages().send(userId="me", body=message).execute()
    print(f"Sent: {sent['id']}")


if __name__ == "__main__":
    main()
