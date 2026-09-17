#!/usr/bin/env python3
"""Orchestrates one full, unattended newsletter issue - the entry point Trigger.dev calls.

Pipeline: pick a topic (avoiding recent repeats) -> research it -> synthesize the branded
brief (with a grounding check) -> generate images/chart -> build the HTML -> save to Drive ->
email a review copy to Kislay ONLY (no bcc to the real subscriber list - that's a deliberate
choice, see workflows/newsletter_automation.md) -> best-effort local archive export.

This keeps all orchestration logic in Python (where the existing tools already live) rather
than in the Trigger.dev Node task, which just invokes this one script - see
trigger.config.ts / src/trigger/newsletter.ts.

Usage:
    python tools/run_scheduled_issue.py
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import drive_client  # noqa: E402

TOOLS_DIR = Path(__file__).parent
REVIEW_RECIPIENT = "kislayranjan@gmail.com"


def run(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(f"Command failed ({' '.join(cmd)})")
    return result.stdout.strip().splitlines()[-1].strip()


def main():
    print("=== Monk10x scheduled newsletter run ===")
    today = datetime.date.today().isoformat()

    print("Reading topic history from Drive...")
    history = drive_client.read_topic_history()

    print("Picking a topic...")
    topic_json = run([sys.executable, str(TOOLS_DIR / "pick_topic.py"), "--history", json.dumps(history)])
    picked = json.loads(topic_json)
    topic, audience = picked["topic"], picked["audience"]
    print(f"Topic: {topic} (audience: {audience})")
    drive_client.append_topic_history(topic)

    slug = "".join(c if c.isalnum() else "-" for c in topic.lower()).strip("-")[:60]

    print("Researching (core angle)...")
    sources_1 = run([
        sys.executable, str(TOOLS_DIR / "research_topic.py"), topic,
        "--audience", audience, "--out", f".tmp/research/{slug}-a-sources.json",
    ])
    print("Researching (business-impact angle)...")
    sources_2 = run([
        sys.executable, str(TOOLS_DIR / "research_topic.py"), f"ROI statistics business impact of {topic}",
        "--audience", audience, "--out", f".tmp/research/{slug}-b-sources.json",
    ])

    print("Synthesizing the branded brief...")
    brief_path = f".tmp/research/{slug}.json"
    run([
        sys.executable, str(TOOLS_DIR / "synthesize_brief.py"),
        "--topic", topic, "--audience", audience,
        "--sources", sources_1, sources_2,
        "--out", brief_path,
    ])
    brief = json.loads(Path(brief_path).read_text(encoding="utf-8"))

    print("Generating hero photo...")
    hero_path = run([
        sys.executable, str(TOOLS_DIR / "generate_infographic.py"), brief["hero_image_prompt"],
        "--style", "photo", "--aspect-ratio", "16:9", "--out", f".tmp/images/{slug}-hero.png",
    ])
    print("Generating supporting photo...")
    support_path = run([
        sys.executable, str(TOOLS_DIR / "generate_infographic.py"), brief["support_image_prompt"],
        "--style", "photo", "--aspect-ratio", "16:9", "--out", f".tmp/images/{slug}-support.png",
    ])
    print("Rendering business-impact chart...")
    chart_path = run([
        sys.executable, str(TOOLS_DIR / "generate_chart.py"),
        json.dumps(brief["business_impact_chart"]), "--out", f".tmp/images/{slug}-chart.png",
    ])

    print("Building HTML...")
    html_path = run([
        sys.executable, str(TOOLS_DIR / "build_newsletter_html.py"), brief_path,
        "--cta-text", brief.get("cta_suggestion", "Get in touch"),
        "--out", f".tmp/newsletter_{slug}.html",
    ])
    html = Path(html_path).read_text(encoding="utf-8")

    print("Saving to Drive...")
    drive_title = f"[Auto-draft] {topic} — {today}"
    drive_file_id = drive_client.upload_html(html, drive_title)
    print(f"Drive file: https://drive.google.com/file/d/{drive_file_id}/view")

    print("Exporting local archive (best-effort)...")
    archive_note = "skipped (Playwright/Chromium unavailable in this environment)"
    try:
        pdf_path = run([
            sys.executable, str(TOOLS_DIR / "export_newsletter_pdf.py"),
            "--html", html_path, "--hero-image", hero_path,
            "--support-image", support_path, "--chart-image", chart_path,
            "--issue-number", "0", "--date", today, "--out-dir", ".tmp/archive",
        ])
        drive_client.upload_binary(pdf_path, f"[Auto] {topic} - {today}.pdf",
                                    drive_client.AUTO_ARCHIVE_FOLDER_ID, "application/pdf")
        archive_note = "uploaded to Drive Auto-archive folder"
    except SystemExit as e:
        print(f"PDF export failed, continuing without it: {e}", file=sys.stderr)

    print(f"Sending review copy to {REVIEW_RECIPIENT}...")
    run([
        sys.executable, str(TOOLS_DIR / "send_newsletter.py"),
        "--html", html_path, "--hero-image", hero_path,
        "--support-image", support_path, "--chart-image", chart_path,
        "--to", REVIEW_RECIPIENT,
        "--subject", f"[Auto-draft for review] {brief.get('hook', topic)}",
    ])

    word_count = len(html.split())  # rough, includes markup - fine for a sanity log line
    print("=== Done ===")
    print(f"Topic: {topic}")
    print(f"Drive record: https://drive.google.com/file/d/{drive_file_id}/view")
    print(f"Local archive: {archive_note}")
    print("Sent to review recipient only (no subscriber bcc, per standing policy).")


if __name__ == "__main__":
    main()
