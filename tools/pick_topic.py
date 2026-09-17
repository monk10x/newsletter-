#!/usr/bin/env python3
"""Pick a fresh newsletter topic via the Anthropic API, avoiding recent repeats.

Used by the scheduled (Trigger.dev) pipeline in place of Kislay giving a topic by hand.
Interactive runs should keep getting topics from Kislay directly - this is specifically for
the unattended path.

Usage:
    python tools/pick_topic.py --history '["topic one", "topic two"]'
    python tools/pick_topic.py --history-file .tmp/topic_history.json

Prints a JSON object {"topic": "...", "audience": "..."} to stdout.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You pick topics for the Monk10x newsletter. Monk10x is an AI automation \
and digital systems studio for small and medium businesses - positioning: "AI automation + \
digital systems partner for businesses that want to move from manual work to intelligent \
workflows." Brand voice: clear, direct, technical but understandable, never hyped.

Pick ONE fresh topic for the next issue, in the space of: AI automation for SMB operations, \
customer engagement/outreach, marketing automation, AI agents, business impact/ROI of \
automation, or adjacent practical business-systems topics. It must be genuinely different \
from the recent topics list you're given (different angle, not just reworded).

Return ONLY valid JSON, no markdown fences, no commentary:
{"topic": "specific, concrete topic phrase (not a vague theme)", "audience": "who this issue is for, e.g. 'small and medium business owners'"}"""


def pick_topic(recent_topics: list) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Missing ANTHROPIC_API_KEY in .env")

    client = anthropic.Anthropic(api_key=api_key)
    recent_str = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "(none yet)"
    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Recent topics (don't repeat these angles):\n{recent_str}"}],
    )
    text_blocks = [block.text for block in message.content if block.type == "text"]
    text = "".join(text_blocks).strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"Could not parse topic JSON ({e}). Raw output:\n{text[:500]}")


def main():
    parser = argparse.ArgumentParser(description="Pick a fresh Monk10x newsletter topic")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--history", default=None, help="JSON array of recent topic strings")
    group.add_argument("--history-file", default=None, help="Path to a JSON file with {\"topics\": [...]}")
    args = parser.parse_args()

    if args.history:
        recent = json.loads(args.history)
    elif args.history_file:
        recent = json.loads(Path(args.history_file).read_text(encoding="utf-8")).get("topics", [])
    else:
        recent = []

    result = pick_topic(recent)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
