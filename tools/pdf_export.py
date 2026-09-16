"""Shared HTML-to-PDF rendering, used by export_newsletter_pdf.py and export_blog_pdf.py.

Renders with Playwright/Chromium (not WeasyPrint - that needs GTK/Pango libraries this
Windows machine doesn't have, see workflows/newsletter_automation.md Known constraints).
"""
import base64
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def data_uri(path: Path, mime: str = "image/png") -> str:
    if not path.exists():
        sys.exit(f"Image not found: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def inline_images(html: str, cid_to_path: dict) -> str:
    """Replace cid:<name> references in html with embedded data: URIs."""
    for cid, path in cid_to_path.items():
        html = html.replace(f"cid:{cid}", data_uri(Path(path)))
    return html


def render_pdf(html: str, out_path: Path, width: str = "650px") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": int(width.rstrip("px")), "height": 800})
        page.set_content(html, wait_until="networkidle")
        height = page.evaluate(
            "Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
        )
        # A tall single-page PDF (not standard Letter/A4 pagination) so the document reads
        # as one continuous archive page. Overshooting the height slightly is safe (trailing
        # whitespace); undershooting spills a near-blank extra page - round up generously.
        page.pdf(
            path=str(out_path),
            width=width,
            height=f"{height + 20}px",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()


def render_png(html: str, out_path: Path, width: int = 650, scale: int = 2) -> None:
    """Render as a single full-page PNG (not paginated) - sharper than rasterizing the PDF,
    and simpler since it skips the PDF height-buffer workaround entirely."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": width, "height": 800},
            device_scale_factor=scale,
        )
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=str(out_path), full_page=True)
        browser.close()
