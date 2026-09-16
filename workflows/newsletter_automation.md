# Workflow: Newsletter Automation

## Objective
Take a topic from Kislay, turn it into one branded Monk10x newsletter issue, and get it
into subscriber inboxes, into Drive, and into the local archive (PDF and PNG).

**Format rules, set by Kislay on 2026-09-16 after two rounds of feedback — these are the
standing target, not a one-off:**
- **4-5 section headers, ~600-800 words total.** Not a long-form article — a scannable,
  visual brief. (First draft had 5 thin bullets and one image → "too short and bland." Second
  draft had 7 sections and ~1000+ words of prose → "not too text-heavy," corrected to "4-5
  headers" after a typo said "45.") The current template (`newsletter_template.html.j2`) has
  5 headers — What's happening, Business impact, The playbook, Why it matters, Sources — and
  is bullet-first throughout, no long paragraphs.
- **No workflow/node-diagram infographics.** Use real-world photography (`--style photo` in
  `generate_infographic.py`) for the hero/supporting images, and a real matplotlib chart
  (`generate_chart.py`) for any numeric comparison — never an AI-generated "chart-style" image.
- **Deliverable formats: PNG and PDF, both from the same HTML.** PNG (`export_newsletter_png.py`,
  a full-page Playwright screenshot) is the primary shareable-graphic format; PDF
  (`export_newsletter_pdf.py`) remains the document-style archive. Generate both for every issue.

## Required input
- **Topic** (required): what the issue is about, e.g. "AI automation for SMB customer
  contact and FOMO".
- **Audience** (optional): who this issue is speaking to, e.g. "small and medium business
  owners". Defaults to Monk10x's general audience (operators/founders evaluating AI automation).
- **CTA** (optional): the call-to-action link/text for this issue. Defaults to a generic
  "get in touch" link if not given — ask Kislay for the real one before sending if this
  issue is meant to drive a specific action (audit call, waitlist, etc.).
- **Send now vs. draft**: always confirm with Kislay before the final send (see Step 6).
  Never send to the full subscriber list without an explicit go-ahead on that specific issue.

## Pipeline

### Step 1 — Research (2 calls is usually enough)
Deterministic search (the tool), then synthesis into the newsletter's structure (the agent).
Two research angles cover the current 5-section template well:
```
python tools/research_topic.py "<core topic>" [--audience "<audience>"]
python tools/research_topic.py "ROI statistics business impact of <topic>"
```
- The first covers "What's happening" — core facts, plus 1-2 recent/dated developments if
  relevant (add `--topic-type news` as a third call only if the topic is genuinely news-driven).
- The second feeds "Business impact" — look specifically for **comparable numeric stats**.
  Percentages work best for one chart; don't mix % and $-multiple metrics on the same chart —
  put whichever doesn't fit into a text bullet instead.
- Output: one `.tmp/research/<slug>-sources.json` per call.

**1b — Synthesize the brief.** Read the sources files and write `.tmp/research/<topic-slug>.json`
by hand, matching this schema exactly (consumed by `build_newsletter_html.py` in Step 3) —
it's deliberately compact and bullet-first, not prose:
```json
{
  "topic": "string, the topic as given",
  "hook": "one sharp sentence to open the newsletter, no hype",
  "subhead": "one sentence, not a paragraph - replaces what used to be a 'problem' paragraph",
  "whats_happening": [
    {"point": "one sentence, ~20-30 words, concrete fact/stat/development", "source_url": "https://..."}
  ],
  "business_impact_bullets": [
    {"point": "one sentence with a real number", "source_url": "https://..."}
  ],
  "playbook_bullets": [
    "one short sentence of our own synthesis, no source needed"
  ],
  "why_it_matters_bullets": [
    "one short sentence"
  ],
  "cta_suggestion": "one short, specific suggested call-to-action for the newsletter",
  "hero_image_prompt": "a real-world photography scene (people, workspaces) illustrating the topic - NOT a diagram",
  "support_image_prompt": "a second real-world photography scene, optional",
  "business_impact_chart": {
    "title": "chart title",
    "unit": "%",
    "bars": [{"label": "...", "value": 21}]
  },
  "sources": [{"title": "...", "url": "..."}]
}
```
Rules for this step:
- Write in Monk10x's voice (clear, direct, technical but understandable, never hyped or
  buzzword-heavy) — and keep every bullet to one sentence. If a point needs two sentences to
  land, it's two bullets, not a paragraph.
- Every `whats_happening`/`business_impact_bullets` entry must trace to a real result from a
  sources file — its `source_url` must be a URL Tavily actually returned. Don't fabricate a
  stat. Aim for 6-7 `whats_happening` bullets and 3-4 `business_impact_bullets`.
- `business_impact_chart.bars` must be **real numbers from real sources** — never invent
  chart data (see Known constraints). Keep all bars in the same unit.
- `playbook_bullets` (3-4) and `why_it_matters_bullets` (2-3) are the agent's own synthesis —
  no citation needed, but keep them grounded in what the research actually supports.
- `sources` is the full deduplicated reading list — populates the footer.
- Check the total word count before moving on: strip HTML tags from the built output and
  count words (`python -c "import re; t=re.sub('<[^>]+>',' ',open('.tmp/newsletter_X.html',encoding='utf-8').read()); print(len(re.sub(chr(92)+'s+',' ',t).split()))"`
  after Step 2) — target 600-800. Under 600, add one more bullet to the thinnest section
  (don't pad existing bullets into longer sentences). Over 800, cut a bullet, don't shorten
  the citations.

### Step 2 — Generate the images
Three assets:
```
python tools/generate_infographic.py "<hero_image_prompt>" --style photo --aspect-ratio 16:9
python tools/generate_infographic.py "<support_image_prompt>" --style photo --aspect-ratio 16:9
python tools/generate_chart.py '<business_impact_chart JSON from the brief>' --out .tmp/images/chart-<slug>.png
```
- `--style photo` (real-world documentary photography) is the default for the newsletter —
  `--style diagram` (node/workflow style) exists in the tool but is retired for newsletters
  per the format rules above.
- `generate_chart.py` renders with matplotlib from real `bars` data — deterministic, never an
  AI image call, because chart numbers must be accurate.
- Downloads/renders happen immediately to `.tmp/images/` (Kie.ai URLs expire ~24h).
- **Look at every generated photo before moving on**: no hallucinated fake logo/wordmark, no
  garbled on-screen text meant to be legible, authentic/candid framing.

### Step 3 — Build the HTML
```
python tools/build_newsletter_html.py .tmp/research/<slug>.json \
  --issue-number <N> --cta-text "<cta text>" --cta-url "<cta link>"
```
- Renders `tools/templates/newsletter_template.html.j2` with brand tokens from `tools/brand.py`.
  The chart section and supporting photo render conditionally (`--no-chart` / `--no-support-image`
  to omit either).
- Output: `.tmp/newsletter_<slug>.html`.
- Images are referenced by Content-ID: `cid:monk10x_logo`, `cid:newsletter_hero_image`,
  `cid:newsletter_support_image`, `cid:newsletter_chart_image` (constants in `tools/brand.py`).
  These only resolve once Step 5/6/7 attach or inline the matching files — the raw HTML shows
  broken images in a browser, that's expected.
- Run the word-count check from Step 1b now, against this built file.
- Track the issue number yourself (check the Newsletters Drive folder or local `Newsletters/`
  folder for the last one used) — there's no state file for it.

### Step 4 — Save to Drive (agent step, not a script)
Use the Google Drive MCP connector directly (already authorized against `Growth@monk10x.com`):
- Target folder: **Monk10x → Newsletters** (folder ID `1iypzgJgZpscZKrhpLHhDvvKkzgAhbTHw`).
- `create_file` with `title` like `Issue <N> — <topic> — <YYYY-MM-DD>`, `textContent` set to
  the built HTML, `contentMimeType: text/html`, `parentId` the Newsletters folder ID, and
  `disableConversionToGoogleType: true` (keep it as an .html file, not converted to a Google
  Doc). This is the permanent record — do this even if the send in Step 6 is just a test.
- If revising an issue already saved (e.g. correcting length/format), save the new version
  with a `(v2)`/`(v3)` suffix rather than trying to overwrite — `create_file` always makes a
  new file. Mention the superseded version to Kislay rather than silently leaving stale copies.

### Step 5 — Read the subscriber list (agent step, not a script)
- The list lives in the **"Monk10x Newsletter Subscribers"** Google Sheet in the Monk10x
  Drive folder (file ID `1Nr4JMwTgOwZ308XGIiqwLEuO6VExMSqCDnTG4uSrPzg`), columns:
  `Email, Name, Status, Subscribed Date`.
- Use Google Drive MCP's `read_file_content` on that file ID, parse it, and only send to
  rows where `Status = active`.
- This sheet currently only has Kislay's own address seeded in it as a placeholder — treat
  any "send to everyone" request as sending to that single address until real subscribers
  are added.

### Step 6 — Send
```
python tools/send_newsletter.py \
  --html .tmp/newsletter_<slug>.html \
  --hero-image .tmp/images/<file>.png \
  --support-image .tmp/images/<file>.png \
  --chart-image .tmp/images/chart-<slug>.png \
  --to kislayranjan@gmail.com \
  --subject "<subject line>"
```
This is a real script, not an agent/MCP step — see **Known constraints** below for why.
- `--support-image`/`--chart-image` are optional (match whatever `--no-support-image`/
  `--no-chart` was passed in Step 3) — `--hero-image` is required.
- `--subject`: the brief's `hook` (short, declarative, no hype).
- Builds the raw MIME message itself (`multipart/related`: HTML + inline images with real
  `Content-ID` headers) and sends via the Gmail API. The logo attaches automatically from
  `Brand Assets/monk_logo_transparent.png`.
- Requires one-time OAuth setup — see the docstring at the top of `tools/send_newsletter.py`.
  `credentials.json`/`token.json` are gitignored; don't commit them.
- **Before sending to the real list**: send with `--to kislayranjan@gmail.com` only (no
  `--bcc`), get explicit sign-off on subject/content/CTA/length, and confirm every image
  rendered inline. Only then re-run with `--bcc` set to all active subscriber addresses.
  Never send to the full list without an explicit go-ahead on that issue.
- Don't resend automatically just because the content changed — ask first. Not every
  revision (e.g. a format/length fix) needs a fresh email; confirm whether Kislay wants a
  re-send or just an updated archive copy.

### Step 7 — Export the local archive (PNG + PDF)
```
python tools/export_newsletter_png.py \
  --html .tmp/newsletter_<slug>.html \
  --hero-image .tmp/images/<file>.png \
  --support-image .tmp/images/<file>.png \
  --chart-image .tmp/images/chart-<slug>.png \
  --issue-number <N> [--date YYYY-MM-DD]

python tools/export_newsletter_pdf.py \
  --html .tmp/newsletter_<slug>.html \
  --hero-image .tmp/images/<file>.png \
  --support-image .tmp/images/<file>.png \
  --chart-image .tmp/images/chart-<slug>.png \
  --issue-number <N> [--date YYYY-MM-DD]
```
- Both share `tools/pdf_export.py` for the `cid:` → `data:` URI swap (PDF/PNG rendering has
  no email client to resolve Content-IDs) and both render as **one continuous image/page**,
  not paginated Letter/A4.
- PNG is a full-page Playwright screenshot at 2x scale — sharper than rasterizing the PDF, and
  the primary "shareable graphic" deliverable per the format rules above.
- Output: `Newsletters/Issue <NN> - <date>.png` and `.pdf` in the **project root** (local D:
  drive) — separate from the Drive "Newsletters" folder used in Step 4. Keep all three copies
  (Drive HTML, local PDF, local PNG). Re-running with the same issue number/date overwrites
  the local file in place.
- Before a real send, export a throwaway preview (e.g. `--date <date>-preview`) and read it
  back to visually QA the whole layout — including a manual header-count and word-count
  sanity check against the format rules — before sending anything. Delete the preview file
  afterward.

## Tools
| Tool | Purpose |
|---|---|
| `tools/research_topic.py` | Tavily Search API — web-grounded source fetch (usually 2 calls per issue; synthesis into the brief is an agent step, not this script) |
| `tools/generate_infographic.py` | Kie.ai Nano Banana — `--style photo` (default for newsletter) for real-world imagery, `--style diagram` for the old workflow-diagram look (retired for newsletters) |
| `tools/generate_chart.py` | matplotlib — renders a branded bar chart from real data (never AI-generated) |
| `tools/build_newsletter_html.py` | Renders the branded, bullet-first HTML from the research brief |
| `tools/send_newsletter.py` | Sends via Gmail API (OAuth) with real inline images |
| `tools/export_newsletter_png.py` | Full-page PNG screenshot for the local `Newsletters/` archive (primary shareable format) |
| `tools/export_newsletter_pdf.py` | Single-page PDF for the local `Newsletters/` archive |
| `tools/pdf_export.py` | Shared rendering logic (image inlining + Playwright PDF/PNG render), used by both the newsletter and blog exporters |
| `tools/brand.py` | Single source of truth for brand colors/fonts/tokens/Content-IDs |
| `tools/templates/newsletter_template.html.j2` | The email layout itself — 5 headers, bullet-first |
| Google Drive MCP connector | Save the issue to Drive, read the subscriber sheet |

Setup: `pip install -r requirements.txt`, then fill in `TAVILY_API_KEY` and `KIE_API_KEY`
in `.env` (see `.env.example`). Drive needs no keys — it runs through the already authorized
Claude Code connector, which is why Steps 4-5 are agent actions rather than `tools/*.py`
scripts. Gmail sending needs the one-time OAuth setup described in `tools/send_newsletter.py`.
PNG/PDF export need a one-time `python -m playwright install chromium` after `pip install`
(already done on this machine).

## Known constraints / things learned
- **The newsletter's length and structure went through two corrections before landing** — see
  the format rules at the top. If asked to "add more" again, add more *sourced bullets*, not
  more prose paragraphs or more section headers past 5.
- **No workflow-diagram imagery in the newsletter** — use `--style photo`. The `diagram` style
  still exists in `generate_infographic.py` for other uses, but don't default to it here.
- **Chart data must come from real sources, rendered deterministically** — `generate_chart.py`
  uses matplotlib against numbers you supply, specifically because an AI image model asked to
  "draw a chart" will invent plausible-looking but fake numbers. Keep every bar in one chart
  to the same unit.
- **matplotlib chart titles need manual wrapping** — a long title otherwise runs off the
  figure edge. `generate_chart.py` wraps at 48 characters via `textwrap.wrap()`; if titles
  still clip, widen the figure or lower the wrap width, don't just shrink the font.
- **Kie.ai result URLs expire ~24h.** Both image tools download/render immediately — never
  store just the remote URL and come back to it later.
- **Tavily is search-only** — it returns sourced results and a short summary `answer`, but not
  a structured, on-brand brief. The synthesis step (1b) is deliberately an agent action, not
  hardcoded into a script.
- **The Gmail MCP connector strips every `<img>` tag from `htmlBody`, unconditionally** —
  confirmed 2026-09-16 by testing `cid:`, `data:`, and plain `https:` sources on
  `send_message` and pulling the sent message back with `get_message`: the tag was gone every
  time, while `<table>`/`<b>` survived fine. This is why sending is a real script
  (`tools/send_newsletter.py`) that builds the raw MIME message itself. If a future connector
  update seems to fix this, verify with the same test before switching back — don't assume it
  works from the send succeeding alone.
- **`Brand Assets/monk_logo_transparent.png` has a black wordmark and black hand icon on a
  transparent background — it only reads correctly on a white/light background**, despite the
  brand guidelines PDF's "Preferred background: Black or very dark neutral" line for the
  master logo (confirmed by rendering the actual file). That guideline likely describes a
  reversed/one-color variant that was never supplied. The email header uses a white background
  for this reason.
- The subscriber list starts with exactly one address (Kislay's). Don't treat a "full send"
  as reaching real subscribers until the sheet has real ones.
- **WeasyPrint doesn't work on this Windows machine** (missing `libgobject-2.0-0`/Pango/GTK) —
  `pdf_export.py` uses Playwright/Chromium instead. Don't re-attempt WeasyPrint here.
- **PDF export needs a small height buffer.** Setting the custom PDF page height to exactly
  `document.body.scrollHeight` produced a spurious, fully blank second page. Adding ~20px of
  slack fixed it (`pdf_export.render_pdf()`). The PNG path (`render_png`, full-page screenshot)
  doesn't have this problem at all, which is one reason it's now the primary format.

## Edge cases
- **A section looks thin (fewer than ~4 bullets, or a bullet with no real citation)**: re-run
  that research call with a more specific topic phrasing — don't ship a thin section, and
  don't pad it with an uncited claim.
- **Business-impact stats from different sources don't share a unit**: don't force them into
  one chart — put the chartable (same-unit) numbers in `business_impact_chart` and the rest as
  plain `business_impact_bullets` text.
- **Word count won't land in 600-800 without padding**: prefer landing slightly under 600 with
  tight, genuinely useful bullets over hitting 800 by restating things. The floor matters less
  than "not too text-heavy."
- **Infographic/photo generation fails/times out**: retry once; if it fails again, simplify
  the prompt (very long or compound prompts are more failure-prone).
- **API keys missing**: the Python tools exit with a clear "Missing X_API_KEY in .env"
  message rather than a stack trace — check `.env` first.
