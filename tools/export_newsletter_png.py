#!/usr/bin/env python3
"""Export a built newsletter issue to PNG (full-page screenshot, 2x scale).

Same cid: -> data: URI swap as export_newsletter_pdf.py (see tools/pdf_export.py), but
rendered as a single sharp PNG image instead of a PDF - useful when the deliverable is a
shareable graphic/infographic-style image rather than a document.

Usage:
    python tools/export_newsletter_png.py \
        --html .tmp/newsletter_<slug>.html \
        --hero-image .tmp/images/<file>.png \
        [--support-image .tmp/images/<file>.png] \
        [--chart-image .tmp/images/chart-<slug>.png] \
        --issue-number 3 \
        [--date 2026-09-16] [--out-dir Newsletters]
"""
import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import brand  # noqa: E402
import pdf_export  # noqa: E402

LOGO_PATH = Path("Brand Assets/monk_logo_transparent.png")


def main():
    parser = argparse.ArgumentParser(description="Export a Monk10x newsletter issue to PNG")
    parser.add_argument("--html", required=True, help="Path to the built newsletter HTML")
    parser.add_argument("--hero-image", required=True, help="Path to the issue's hero photo")
    parser.add_argument("--support-image", default=None, help="Optional second inline photo")
    parser.add_argument("--chart-image", default=None, help="Optional business-impact chart PNG")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--out-dir", default="Newsletters", help="Local archive folder (project-relative)")
    args = parser.parse_args()

    html = Path(args.html).read_text(encoding="utf-8")
    cid_map = {brand.LOGO_CID: LOGO_PATH, brand.NEWSLETTER_HERO_CID: args.hero_image}
    if args.support_image:
        cid_map[brand.NEWSLETTER_SUPPORT_CID] = args.support_image
    if args.chart_image:
        cid_map[brand.NEWSLETTER_CHART_CID] = args.chart_image
    html = pdf_export.inline_images(html, cid_map)

    date = args.date or datetime.date.today().isoformat()
    out_path = Path(args.out_dir) / f"Issue {args.issue_number:02d} - {date}.png"

    pdf_export.render_png(html, out_path)
    print(str(out_path))


if __name__ == "__main__":
    main()
