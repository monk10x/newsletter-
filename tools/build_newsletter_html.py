#!/usr/bin/env python3
"""Assemble the branded newsletter HTML from a research brief JSON.

Usage:
    python tools/build_newsletter_html.py .tmp/research/<slug>.json \\
        --issue-number 1 --cta-text "Book a system audit" --cta-url "https://monk10x.com/audit" \\
        [--out .tmp/newsletter_<slug>.html]

Images are referenced by Content-ID (cid:...) for inline email attachments - the sending
step (tools/send_newsletter.py) must attach Brand Assets/monk_logo_transparent.png, the hero
photo, the optional supporting photo, and the optional business-impact chart with matching
Content-IDs (see tools/brand.py for the fixed CIDs).

Research brief schema (see workflows/newsletter_automation.md, Step 1b) - deliberately
compact: 4 section headers, bullet-first, targeting ~600-800 words total per issue:
{
  "topic": "...", "hook": "one sharp sentence", "subhead": "one sentence, not a paragraph",
  "whats_happening": [{"point": "...", "source_url": "..."}],
  "business_impact_bullets": [{"point": "...", "source_url": "..."}]  (optional, pairs with a chart),
  "playbook_bullets": ["...", "..."]  (our own synthesis, no sources needed),
  "why_it_matters_bullets": ["...", "..."],
  "cta_suggestion": "...",
  "sources": [{"title": "...", "url": "..."}]  (optional, full reading list for the footer)
}
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
TEMPLATE_NAME = "newsletter_template.html.j2"


def build(
    brief: dict,
    issue_number: int,
    cta_text: str,
    cta_url: str,
    unsubscribe_url: str,
    has_support_image: bool,
    has_chart: bool,
) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template(TEMPLATE_NAME)

    issue_date = datetime.date.today().strftime("%B %d, %Y")

    return template.render(
        subject=brief.get("hook", brief.get("topic", "Monk10x Newsletter")),
        topic=brief.get("topic", ""),
        hook=brief.get("hook", ""),
        subhead=brief.get("subhead", ""),
        whats_happening=brief.get("whats_happening", []),
        business_impact_bullets=brief.get("business_impact_bullets", []),
        playbook_bullets=brief.get("playbook_bullets", []),
        why_it_matters_bullets=brief.get("why_it_matters_bullets", []),
        sources=brief.get("sources", []),
        cta_text=cta_text or brief.get("cta_suggestion", "Get in touch"),
        cta_url=cta_url,
        issue_label=f"Monk10x Newsletter — Issue {issue_number} — {issue_date}",
        unsubscribe_note_url=unsubscribe_url,
        logo_cid=brand.LOGO_CID,
        hero_cid=brand.NEWSLETTER_HERO_CID,
        support_cid=brand.NEWSLETTER_SUPPORT_CID if has_support_image else None,
        chart_cid=brand.NEWSLETTER_CHART_CID if has_chart else None,
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
    parser = argparse.ArgumentParser(description="Build branded Monk10x newsletter HTML")
    parser.add_argument("research_json", help="Path to the research brief JSON")
    parser.add_argument("--issue-number", type=int, default=1)
    parser.add_argument("--cta-text", default=None, help="Defaults to the brief's cta_suggestion")
    parser.add_argument("--cta-url", default="https://monk10x.com")
    parser.add_argument("--unsubscribe-url", default="https://monk10x.com/unsubscribe")
    parser.add_argument("--no-support-image", action="store_true", help="Omit the supporting photo slot")
    parser.add_argument("--no-chart", action="store_true", help="Omit the business-impact chart slot")
    parser.add_argument("--out", default=None, help="Output HTML path (default: .tmp/newsletter_<slug>.html)")
    args = parser.parse_args()

    brief_path = Path(args.research_json)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))

    html = build(
        brief,
        args.issue_number,
        args.cta_text,
        args.cta_url,
        args.unsubscribe_url,
        has_support_image=not args.no_support_image,
        has_chart=not args.no_chart,
    )

    out_path = Path(args.out) if args.out else Path(".tmp") / f"newsletter_{brief_path.stem}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
