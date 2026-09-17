"""Google Drive access for the scheduled (Trigger.dev) pipeline.

This is the Python equivalent of what the Google Drive MCP connector does interactively in a
Claude Code session - MCP only works inside an interactive session, so a headless cron job
needs a real API client instead. Uses tools/google_auth.py for credentials (local file-based
OAuth when run by hand, GOOGLE_* env vars when run by Trigger.dev).

Interactive Claude Code sessions should keep using the MCP connector directly, as documented
in workflows/newsletter_automation.md - this module is specifically for the unattended path.
"""
import io
import json
import sys
from pathlib import Path

from googleapiclient.discovery import build as build_service
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

sys.path.insert(0, str(Path(__file__).parent))
import google_auth  # noqa: E402

MONK10X_FOLDER_ID = "1Ut3E6wOixzzrGP_TVqeTYFZhhd0xyomj"
NEWSLETTERS_FOLDER_ID = "1iypzgJgZpscZKrhpLHhDvvKkzgAhbTHw"
AUTO_ARCHIVE_FOLDER_ID = "1F7bqcLQEQHrisnk7ddhoYxGxGtn-nVbC"
SUBSCRIBERS_SHEET_ID = "1Nr4JMwTgOwZ308XGIiqwLEuO6VExMSqCDnTG4uSrPzg"
TOPIC_HISTORY_FILE_ID = "1Kj-WsW-KU8fJU7qqxIFuMEjandVz5kAP"


def _service():
    creds = google_auth.get_credentials()
    return build_service("drive", "v3", credentials=creds)


def upload_html(html: str, title: str, parent_folder_id: str = NEWSLETTERS_FOLDER_ID) -> str:
    """Uploads as a plain .html file (not converted to a Google Doc), mirroring the MCP
    create_file call with disableConversionToGoogleType used elsewhere in this project."""
    service = _service()
    media = MediaIoBaseUpload(io.BytesIO(html.encode("utf-8")), mimetype="text/html")
    file = service.files().create(
        body={"name": title, "parents": [parent_folder_id]},
        media_body=media,
        fields="id,webViewLink",
    ).execute()
    return file["id"]


def upload_binary(path: str, title: str, parent_folder_id: str, mime_type: str) -> str:
    service = _service()
    media = MediaFileUpload(path, mimetype=mime_type)
    file = service.files().create(
        body={"name": title, "parents": [parent_folder_id]},
        media_body=media,
        fields="id,webViewLink",
    ).execute()
    return file["id"]


def read_sheet_as_rows(file_id: str = SUBSCRIBERS_SHEET_ID) -> list:
    """Exports a Google Sheet as CSV and parses it into a list of dicts keyed by header row -
    same approach the MCP read_file_content call uses (Drive export, not the Sheets API)."""
    import csv

    service = _service()
    csv_bytes = service.files().export(fileId=file_id, mimeType="text/csv").execute()
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
    return list(reader)


def read_topic_history(file_id: str = TOPIC_HISTORY_FILE_ID) -> list:
    service = _service()
    content = service.files().get_media(fileId=file_id).execute()
    return json.loads(content.decode("utf-8")).get("topics", [])


def append_topic_history(topic: str, file_id: str = TOPIC_HISTORY_FILE_ID) -> None:
    service = _service()
    topics = read_topic_history(file_id)
    topics.append(topic)
    topics = topics[-30:]  # keep it bounded
    media = MediaIoBaseUpload(
        io.BytesIO(json.dumps({"topics": topics}, indent=2).encode("utf-8")),
        mimetype="application/json",
    )
    service.files().update(fileId=file_id, media_body=media).execute()
