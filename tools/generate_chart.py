#!/usr/bin/env python3
"""Render a branded bar chart from real data (matplotlib, not an AI image).

Charts represent real numbers, so they're generated deterministically from data you
provide - never ask an image model to "draw a chart," it will invent numbers.

Usage:
    python tools/generate_chart.py '{"title": "...", "unit": "%", "bars": [{"label": "...", "value": 21}, ...]}' \
        [--out path.png]

Or pass a path to a JSON file instead of inline JSON as the first argument.
"""
import argparse
import json
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import brand  # noqa: E402


def render(data: dict, out_path: Path) -> None:
    bars = data["bars"]
    labels = [b["label"] for b in bars]
    values = [b["value"] for b in bars]
    unit = data.get("unit", "")

    fig, ax = plt.subplots(figsize=(10.5, 0.7 * len(bars) + 1.5), dpi=200)
    fig.patch.set_facecolor(brand.WHITE)
    ax.set_facecolor(brand.WHITE)

    y_pos = range(len(labels))
    bars_artist = ax.barh(y_pos, values, color=brand.ELECTRIC_BLUE, height=0.55, zorder=3)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=12, color=brand.MONK_BLACK)
    ax.invert_yaxis()

    for spine in ("top", "right", "left", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0, labelsize=10, colors=brand.SYSTEM_GRAY)
    ax.set_xticks([])

    max_val = max(values) if values else 1
    for bar, value in zip(bars_artist, values):
        ax.text(
            bar.get_width() + max_val * 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{value}{unit}",
            va="center",
            ha="left",
            fontsize=12,
            fontweight="bold",
            color=brand.MONK_BLACK,
        )

    ax.set_xlim(0, max_val * 1.18)

    if data.get("title"):
        wrapped_title = "\n".join(textwrap.wrap(data["title"], width=48))
        ax.set_title(wrapped_title, fontsize=15, fontweight="bold", color=brand.MONK_BLACK, loc="left", pad=14)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Render a branded bar chart from real data")
    parser.add_argument("data", help="Inline JSON, or a path to a JSON file")
    parser.add_argument("--out", default=None, help="Output PNG path (default: .tmp/images/chart-<slug>.png)")
    args = parser.parse_args()

    data_arg = Path(args.data)
    if data_arg.exists():
        data = json.loads(data_arg.read_text(encoding="utf-8"))
    else:
        data = json.loads(args.data)

    if args.out:
        out_path = Path(args.out)
    else:
        slug = "".join(c if c.isalnum() else "-" for c in data.get("title", "chart")).lower().strip("-")
        out_path = Path(".tmp/images") / f"chart-{slug}.png"

    render(data, out_path)
    print(str(out_path))


if __name__ == "__main__":
    main()
