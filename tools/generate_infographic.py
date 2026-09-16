#!/usr/bin/env python3
"""Generate a branded image with Nano Banana via Kie.ai, and download the result.

Two styles, since the newsletter and the blog need different visual languages:
  - diagram (default): the brand's node/workflow-diagram style, used for newsletter
    infographics. Palette-restricted, no photorealism.
  - photo: real-world, documentary-style photography (real people/workspaces per the
    brand guidelines' "Photography" row) - used for blog articles that explicitly
    should NOT use workflow-diagram imagery. No palette restriction (real photos
    aren't recolored to fit a 5-color palette), no diagram/UI elements.

Usage:
    python tools/generate_infographic.py "prompt" [--style diagram|photo] [--out path.png] [--aspect-ratio 16:9]

API contract (docs.kie.ai/market/google/nano-banana, confirmed 2026-09-16):
    POST https://api.kie.ai/api/v1/jobs/createTask
    GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId=...
Result URLs from Kie.ai expire ~24h after generation, so this tool downloads the image
immediately rather than returning the remote URL.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CREATE_TASK_URL = "https://api.kie.ai/api/v1/jobs/createTask"
RECORD_INFO_URL = "https://api.kie.ai/api/v1/jobs/recordInfo"

STYLE_SUFFIXES = {
    "diagram": (
        " Style: Monk10x brand — engineered and technical, not futuristic hype. "
        "Palette restricted to near-black (#101010), electric blue (#3DA9FC), "
        "compound yellow (#FBBF24) as a sparing accent, system gray (#828282), and white. "
        "Clean geometric shapes, rounded rectangles, connected nodes and lines, structured grid. "
        "No robots, no generic AI brain/circuit clip art, no photorealistic humans. "
        "Do not include any logo, wordmark, brand name, or the text 'Monk10x' anywhere in the "
        "image — the real logo is added separately when this is placed in the email, and this "
        "image must not attempt to recreate it. Keep every text label to one or two short words, "
        "and spell each label exactly as given — double-check spelling before finalizing. "
        "Show an actual workflow, diagram, interface, or before/after — concrete, not decorative."
    ),
    "photo": (
        " Style: real-world documentary photography, per Monk10x's brand guidelines — "
        "real people, workspaces, operators, in authentic environments, not generic corporate "
        "stock photography. Natural lighting, candid framing, shallow depth of field where "
        "appropriate. No illustration, no diagram elements, no UI overlays, no text/labels "
        "rendered in the image, no logos or wordmarks, no robots or generic AI/brain imagery. "
        "Photorealistic, believable, ordinary — not staged-looking or overly polished."
    ),
}


def create_task(prompt: str, api_key: str, model: str, aspect_ratio: str, style: str) -> str:
    payload = {
        "model": model,
        "input": {
            "prompt": prompt + STYLE_SUFFIXES[style],
            "output_format": "png",
            "aspect_ratio": aspect_ratio,
        },
    }
    resp = requests.post(
        CREATE_TASK_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if not resp.ok:
        sys.exit(f"Kie.ai createTask error {resp.status_code}: {resp.text[:1000]}")
    data = resp.json()
    task_id = data.get("data", {}).get("taskId")
    if not task_id:
        sys.exit(f"Kie.ai createTask did not return a taskId: {json.dumps(data)[:800]}")
    return task_id


def poll_task(task_id: str, api_key: str, timeout_s: int = 180, interval_s: int = 4) -> list:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = requests.get(
            RECORD_INFO_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"taskId": task_id},
            timeout=30,
        )
        if not resp.ok:
            sys.exit(f"Kie.ai recordInfo error {resp.status_code}: {resp.text[:1000]}")
        data = resp.json().get("data", {})
        state = data.get("state")
        if state == "success":
            result = json.loads(data.get("resultJson") or "{}")
            urls = result.get("resultUrls") or []
            if not urls:
                sys.exit(f"Task succeeded but returned no resultUrls: {json.dumps(data)[:800]}")
            return urls
        if state == "fail":
            sys.exit(f"Kie.ai generation failed: {data.get('failMsg') or data.get('failCode')}")
        time.sleep(interval_s)
    sys.exit(f"Timed out after {timeout_s}s waiting on Kie.ai task {task_id}")


def download(url: str, out_path: Path) -> None:
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)


def main():
    parser = argparse.ArgumentParser(description="Generate a Monk10x newsletter infographic")
    parser.add_argument("prompt")
    parser.add_argument("--out", default=None, help="Output PNG path (default: .tmp/images/<timestamp>.png)")
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=["1:1", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "5:4", "4:5", "21:9", "auto"],
    )
    parser.add_argument("--model", default=os.environ.get("KIE_MODEL", "google/nano-banana"))
    parser.add_argument("--style", default="diagram", choices=list(STYLE_SUFFIXES))
    args = parser.parse_args()

    api_key = os.environ.get("KIE_API_KEY")
    if not api_key:
        sys.exit("Missing KIE_API_KEY in .env")

    task_id = create_task(args.prompt, api_key, args.model, args.aspect_ratio, args.style)
    urls = poll_task(task_id, api_key)

    out_path = Path(args.out) if args.out else Path(".tmp/images") / f"{task_id}.png"
    download(urls[0], out_path)
    print(str(out_path))


if __name__ == "__main__":
    main()
