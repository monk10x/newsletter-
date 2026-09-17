#!/usr/bin/env python3
"""Synthesize the branded, sourced newsletter brief via the Anthropic API.

This is Step 1b of workflows/newsletter_automation.md turned into code - reading raw Tavily
sources and writing the structured, on-brand, bullet-first brief that
build_newsletter_html.py consumes. Interactive runs should keep doing this step by hand (an
agent reading sources and writing copy is a judgment call, done well); this script exists so
the unattended Trigger.dev pipeline has an equivalent.

Grounding check: after the LLM returns the brief, every source_url it cites in
whats_happening/business_impact_bullets is verified against the URLs actually present in the
input sources files. Anything citing a URL that wasn't in the real results is dropped and
logged, not shipped - this is the guard against a model inventing a plausible-looking but fake
stat. If grounded content drops below the minimum bullet counts, the run fails loudly.

Usage:
    python tools/synthesize_brief.py \
        --topic "..." --audience "..." \
        --sources .tmp/research/a-sources.json .tmp/research/b-sources.json \
        --out .tmp/research/<slug>.json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-5"
MIN_WHATS_HAPPENING = 4
MIN_BUSINESS_IMPACT = 2

SYSTEM_PROMPT = """You write the Monk10x newsletter. Monk10x is an AI automation and digital \
systems studio for small and medium businesses. Brand voice: clear, direct, technical but \
understandable, confident and specific, never hyped or buzzword-heavy (no "revolutionary AI \
transformation" style language). Never vague.

Format rules (Monk10x's standing newsletter format, set after review - do not deviate):
- 600-800 words total across the whole brief. Prefer landing slightly under 600 with tight,
  genuinely useful bullets over hitting 800 by restating things.
- Every bullet is ONE sentence. If a point needs two sentences, it's two bullets, not a
  paragraph. No long prose paragraphs anywhere.
- Ground every factual bullet in the provided sources - you MUST NOT cite a source_url that
  isn't in the "AVAILABLE SOURCES" list below, and you MUST NOT state a stat/fact that isn't
  actually supported by that source's content. If you're not sure a source says something,
  leave it out rather than guess.

Return ONLY valid JSON (no markdown fences, no commentary), matching exactly this schema:
{
  "topic": "the topic as given",
  "hook": "one sharp sentence to open the newsletter, no hype",
  "subhead": "one sentence, not a paragraph",
  "whats_happening": [
    {"point": "one sentence, ~20-30 words, concrete fact/stat/development", "source_url": "https://... (must be from AVAILABLE SOURCES)"}
  ],
  "business_impact_bullets": [
    {"point": "one sentence with a real number", "source_url": "https://... (must be from AVAILABLE SOURCES)"}
  ],
  "playbook_bullets": ["one short sentence of practical synthesis, no source needed", "..."],
  "why_it_matters_bullets": ["one short sentence", "..."],
  "cta_suggestion": "one short, specific call-to-action",
  "hero_image_prompt": "a real-world photography scene (real people/workspaces) illustrating the topic - NOT a diagram, NOT text/UI overlays",
  "support_image_prompt": "a second, different real-world photography scene",
  "business_impact_chart": {
    "title": "chart title",
    "unit": "% (or another single unit - every bar must share the same unit)",
    "bars": [{"label": "short label", "value": 21}]
  },
  "sources": [{"title": "...", "url": "... (must be from AVAILABLE SOURCES)"}]
}
Include 6-7 whats_happening bullets, 3-4 business_impact_bullets, 3-4 playbook_bullets,
2-3 why_it_matters_bullets, 3-5 chart bars (real numbers pulled from the sources, same unit),
and a deduplicated sources list covering everything you cited."""


def load_sources(paths: list) -> tuple:
    """Returns (available_urls_by_title, context_text_for_prompt)."""
    available = {}
    context_parts = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for result in data.get("results", []):
            url = result.get("url")
            if not url or url in available:
                continue
            available[url] = result.get("title", "")
            snippet = (result.get("content") or "")[:1200]
            context_parts.append(f"URL: {url}\nTITLE: {result.get('title', '')}\nCONTENT: {snippet}\n")
    return available, "\n---\n".join(context_parts)


def synthesize(topic: str, audience: str, available: dict, context_text: str) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Missing ANTHROPIC_API_KEY in .env")

    client = anthropic.Anthropic(api_key=api_key)
    user_content = (
        f"TOPIC: {topic}\nAUDIENCE: {audience or 'general Monk10x audience'}\n\n"
        f"AVAILABLE SOURCES (only cite URLs from this list):\n{context_text}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text_blocks = [block.text for block in message.content if block.type == "text"]
    if not text_blocks:
        sys.exit(f"No text block in Anthropic response (got: {[b.type for b in message.content]})")
    text = "".join(text_blocks).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"Could not parse brief JSON ({e}). Raw output:\n{text[:1500]}")


def ground_check(brief: dict, available: dict) -> dict:
    """Drops any bullet/source citing a URL that wasn't actually in the input sources."""
    dropped = []

    def filter_list(items, url_key="source_url"):
        kept = []
        for item in items:
            url = item.get(url_key)
            if url in available:
                kept.append(item)
            else:
                dropped.append((item.get("point", item), url))
        return kept

    brief["whats_happening"] = filter_list(brief.get("whats_happening", []))
    brief["business_impact_bullets"] = filter_list(brief.get("business_impact_bullets", []))
    brief["sources"] = [s for s in brief.get("sources", []) if s.get("url") in available]

    if dropped:
        print(f"WARNING: dropped {len(dropped)} ungrounded bullet(s):", file=sys.stderr)
        for point, url in dropped:
            print(f"  - ({url}) {point}", file=sys.stderr)

    if len(brief["whats_happening"]) < MIN_WHATS_HAPPENING:
        sys.exit(
            f"Only {len(brief['whats_happening'])} grounded whats_happening bullets survived "
            f"(need {MIN_WHATS_HAPPENING}+) - source material is too thin for this topic. "
            "Re-run research with a narrower/different topic rather than shipping a thin issue."
        )
    if len(brief["business_impact_bullets"]) < MIN_BUSINESS_IMPACT:
        sys.exit(
            f"Only {len(brief['business_impact_bullets'])} grounded business_impact bullets "
            f"survived (need {MIN_BUSINESS_IMPACT}+) - re-run research with a stats-focused angle."
        )
    return brief


def main():
    parser = argparse.ArgumentParser(description="Synthesize the Monk10x newsletter brief via Anthropic")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--audience", default=None)
    parser.add_argument("--sources", nargs="+", required=True, help="Paths to research_topic.py output JSON files")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    available, context_text = load_sources(args.sources)
    if not available:
        sys.exit("No sources found in the given files - nothing to ground the brief in.")

    brief = synthesize(args.topic, args.audience, available, context_text)
    brief = ground_check(brief, available)
    brief["topic"] = args.topic

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(brief, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
