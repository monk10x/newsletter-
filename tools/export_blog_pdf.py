#!/usr/bin/env python3
"""Export a built blog article to PDF for the local archive.

Same approach as export_newsletter_pdf.py (see tools/pdf_export.py) - swaps cid:
references for embedded data: URIs, then renders a single continuous page with
Playwright/Chromium. Output goes to "Blog/<slug> - <date>.pdf" in the project root.

Usage:
    python tools/export_blog_pdf.py \
        --html .tmp/blog_<slug>.html \
        --hero-image .tmp/images/<file>.png \
        --support-image .tmp/images/<file>.png \
        [--date 2026-09-16] [--out-dir Blog]
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import brand  # noqa: E402
import pdf_export  # noqa: E402

LOGO_PATH = Path("Brand Assets/monk_logo_transparent.png")


def main():
    parser = argparse.ArgumentParser(description="Export a Monk10x blog article to PDF")
    parser.add_argument("--html", required=True, help="Path to the built blog HTML")
    parser.add_argument("--hero-image", required=True)
    parser.add_argument("--support-image", default=None, help="Optional second inline image")
    parser.add_argument("--slug", default=None, help="Filename slug, defaults to derived from --html")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--out-dir", default="Blog", help="Local archive folder (project-relative)")
    args = parser.parse_args()

    html = Path(args.html).read_text(encoding="utf-8")
    cid_map = {brand.LOGO_CID: LOGO_PATH, brand.BLOG_HERO_CID: args.hero_image}
    if args.support_image:
        cid_map[brand.BLOG_SUPPORT_CID] = args.support_image
    html = pdf_export.inline_images(html, cid_map)

    slug = args.slug or re.sub(r"^blog_|\.html$", "", Path(args.html).name)
    date = args.date or datetime.date.today().isoformat()
    out_path = Path(args.out_dir) / f"{slug} - {date}.pdf"

    pdf_export.render_pdf(html, out_path, width="680px")
    print(str(out_path))


if __name__ == "__main__":
    main()
