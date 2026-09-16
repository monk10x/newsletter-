#!/usr/bin/env python3
"""Fetch web-grounded research sources for a newsletter topic via Tavily.

Usage:
    python tools/research_topic.py "AI agents in customer support" [--audience "..."] [--max-results 8] [--out path.json]

This tool does only the deterministic part: search the web and return sourced results
(Tavily API contract: https://docs.tavily.com/documentation/api-reference/endpoint/search,
confirmed 2026-09-16). It does NOT synthesize the structured newsletter brief (hook, problem,
key_points narrative, system_angle, outcome, compounding, cta_suggestion, image_prompt) -
turning raw sources into on-brand narrative is a judgment call, not a deterministic
transform, so that step is done by the orchestrating agent, not hardcoded here.
See workflows/newsletter_automation.md, Step 1, for what happens with this file's output.

Writes the raw Tavily response (query, answer, results[]) as JSON and prints the path.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int, topic_type: str) -> dict:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        sys.exit("Missing TAVILY_API_KEY in .env")

    payload = {
        "query": query,
        "search_depth": "advanced",
        "topic": topic_type,
        "max_results": max_results,
        "include_answer": "advanced",
        "include_raw_content": False,
    }
    resp = requests.post(
        SEARCH_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if not resp.ok:
        sys.exit(f"Tavily search error {resp.status_code}: {resp.text[:1000]}")
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Fetch grounded research sources for a Monk10x newsletter topic")
    parser.add_argument("topic")
    parser.add_argument("--audience", default=None, help="Who this issue is for; folded into the query for context")
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument(
        "--topic-type",
        default="general",
        choices=["general", "news", "finance"],
        help="Tavily's search topic type (use 'news' for recency-sensitive stories)",
    )
    parser.add_argument("--out", default=None, help="Output JSON path (default: .tmp/research/<slug>-sources.json)")
    args = parser.parse_args()

    query = args.topic
    if args.audience:
        query += f" (relevant to {args.audience})"

    data = search(query, args.max_results, args.topic_type)
    data["_topic"] = args.topic
    data["_audience"] = args.audience

    slug = re.sub(r"[^a-z0-9]+", "-", args.topic.lower()).strip("-")
    out_path = Path(args.out) if args.out else Path(".tmp/research") / f"{slug}-sources.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
