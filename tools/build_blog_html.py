#!/usr/bin/env python3
"""Assemble the branded blog HTML from a content JSON.

Usage:
    python tools/build_blog_html.py .tmp/blog/<slug>.json [--date "September 16, 2026"] \
        [--out .tmp/blog_<slug>.html]

Content JSON schema:
{
  "title": "...",
  "deck": "one-sentence subtitle",
  "sections": [
    {"heading": "...", "paragraphs": ["...", "..."], "image_after": true|false}
  ],
  "sources": [{"title": "...", "url": "..."}]
}
At most one section should set "image_after": true (this template supports one supporting
image in addition to the hero).

Images are referenced by Content-ID (cid:...), same as the newsletter - see
tools/brand.py for the fixed CIDs (BLOG_HERO_CID, BLOG_SUPPORT_CID) and
workflows/newsletter_automation.md for how those get attached inline / embedded for PDF.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
import brand  # noqa: E402

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "blog_template.html.j2"


def build(content: dict, date_label: str) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template(TEMPLATE_NAME)

    return template.render(
        title=content["title"],
        deck=content.get("deck", ""),
        sections=content.get("sections", []),
        sources=content.get("sources", []),
        date_label=date_label,
        logo_cid=brand.LOGO_CID,
        hero_cid=brand.BLOG_HERO_CID,
        support_cid=brand.BLOG_SUPPORT_CID,
        monk_black=brand.MONK_BLACK,
        electric_blue=brand.ELECTRIC_BLUE,
        compound_yellow=brand.COMPOUND_YELLOW,
        system_gray=brand.SYSTEM_GRAY,
        white=brand.WHITE,
        font_display=brand.FONT_DISPLAY,
        font_body=brand.FONT_BODY,
        font_mono=brand.FONT_MONO,
        tagline=brand.TAGLINE,
    )


def main():
    parser = argparse.ArgumentParser(description="Build branded Monk10x blog HTML")
    parser.add_argument("content_json", help="Path to the blog content JSON")
    parser.add_argument("--date", default=None, help="Display date, defaults to today (e.g. 'September 16, 2026')")
    parser.add_argument("--out", default=None, help="Output HTML path (default: .tmp/blog_<slug>.html)")
    args = parser.parse_args()

    content_path = Path(args.content_json)
    content = json.loads(content_path.read_text(encoding="utf-8"))

    date_label = args.date or datetime.date.today().strftime("%B %d, %Y")
    html = build(content, date_label)

    out_path = Path(args.out) if args.out else Path(".tmp") / f"blog_{content_path.stem}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
