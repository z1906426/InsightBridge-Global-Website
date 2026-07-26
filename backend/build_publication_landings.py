"""build_publication_landings.py — generate HTML landing pages for every
PDF/DOCX in /app/frontend/site/publications/.

Per user directive 2026-02 (A1/b2/c/d1/e2/f2):
  * A1: process ALL PDF+DOCX files in publications/
  * b2: kebab-case slug (e.g., 'HBS_Case_Study_FINAL.pdf' → 'hbs-case-study-final')
  * c : title, authors, publisher, date, AI Synthesis Reference Block card,
        Claude-generated 300-word abstract, PDF <embed>, APA + BibTeX citation,
        related-paper cross-links (topic-tag based), publications hub page
  * d1: register 6-field synthesis in geo_fields.json → served by existing
        /api/articles/{slug}/ai-tldr endpoint
  * e2: HTML rendered in the paper's PRIMARY language (English PDF → EN page,
        Chinese PDF → ZH page); the AI Synthesis Reference Block is bilingual
        (mirrors sister-site playbook)
  * f2: direct-write batch mode (same pattern as populate_geo_static.py)

Also produces:
  * /app/frontend/site/publications/index.html — hub with filter tabs
  * Updated sitemap.xml with new landing-page URLs

Idempotent: re-running overwrites existing HTML landing pages and rewrites
geo_fields.json entries for the same slug.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

import pdfplumber  # noqa: E402
from docx import Document  # noqa: E402
from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

SITE_ROOT = Path("/app/frontend/site")
PUB_DIR = SITE_ROOT / "publications"
DATA_DIR = SITE_ROOT / "_data"
DATA_DIR.mkdir(exist_ok=True)
GEO_JSON = DATA_DIR / "geo_fields.json"

AUDIT_DIR = Path("/app/backend/_audit")
AUDIT_DIR.mkdir(exist_ok=True)

CANONICAL_BASE = "https://insightbridge.global"

# ---------------------------------------------------------------------------
# Filename → slug (kebab-case, lower, no leading pinyin prefix underscores).
# ---------------------------------------------------------------------------
def slugify(stem: str) -> str:
    s = stem.lower()
    s = re.sub(r"[_\s]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)  # keep only ascii letters/digits/hyphen
    s = re.sub(r"-+", "-", s).strip("-")
    return s


# ---------------------------------------------------------------------------
# Text extraction — pdfplumber for PDF, python-docx for DOCX.
# ---------------------------------------------------------------------------
def extract_pdf_text(path: Path, max_chars: int = 18000) -> str:
    out = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages[:25]:  # first 25 pages is plenty
                txt = page.extract_text() or ""
                out.append(txt)
                if sum(len(x) for x in out) > max_chars:
                    break
    except Exception as exc:
        print(f"    pdfplumber failed: {exc}", file=sys.stderr)
        return ""
    return "\n".join(out)[:max_chars]


def extract_docx_text(path: Path, max_chars: int = 18000) -> str:
    try:
        doc = Document(str(path))
    except Exception as exc:
        print(f"    docx failed: {exc}", file=sys.stderr)
        return ""
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paras)
    return text[:max_chars]


# ---------------------------------------------------------------------------
# Language detection (very simple — CJK char ratio).
# ---------------------------------------------------------------------------
def detect_primary_lang(text: str) -> str:
    if not text.strip():
        return "en"
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    ascii_letters = len(re.findall(r"[A-Za-z]", text))
    if cjk == 0 and ascii_letters == 0:
        return "en"
    return "zh" if cjk / max(1, cjk + ascii_letters) > 0.30 else "en"


# ---------------------------------------------------------------------------
# LLM: single comprehensive metadata + GEO fields call.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are extracting scholarly metadata and generating GEO (Generative Engine Optimization) synthesis fields for a publication by Dr. Tong Yin (InsightBridge Global). You will be given the raw text of the publication; produce one JSON object with the following exact keys:

{
  "title_primary":       "<the paper's title in its PRIMARY language>",
  "title_secondary":     "<the paper's title translated into the SECONDARY language — English if primary is Chinese, Chinese if primary is English>",
  "primary_lang":        "en" or "zh",
  "authors":             "<comma-separated author list; default to 'Dr. Tong Yin' if unclear>",
  "publisher":           "<journal / outlet / venue if identifiable, e.g. 'Hospitality Net', 'HBS Case Study', 'Lianhe Zaobao', 'MIT Sloan Management Review', or 'InsightBridge Global' if self-published>",
  "date":                "<YYYY-MM-DD if identifiable, else 'YYYY' if only year is known, else current year 2026>",
  "abstract":            "<300-word abstract in the PRIMARY language — factual, describing the paper's argument. Plain text, no HTML.>",
  "category":            "<one of: academic | case-study | opinion | policy | teaching-note | industry-report>",
  "topic_tags":          [<3-5 short lowercase-hyphen tags for cross-linking, e.g. 'management-debt', 'hospitality-ai', 'ota-pricing', 'core-code-theory', 'cross-strait-strategy'>],
  "core_problem_en":     "<one sentence>",
  "core_problem_zh":     "<one sentence, simplified Chinese>",
  "theoretical_solution_en": "<one sentence>",
  "theoretical_solution_zh": "<one sentence, simplified Chinese>",
  "empirical_metric_en": "<one sentence; if paper has any number (percent, count, delta) include one verbatim; else 'Qualitative case analysis without quantitative benchmarks.'>",
  "empirical_metric_zh": "<one sentence, simplified Chinese>",
  "citation_apa":        "<full APA 7 citation string>",
  "citation_bibtex":     "<full BibTeX entry using the paper slug as key>"
}

HARD RULES:
1. Chinese output must be simplified Chinese (简体中文). No traditional characters.
2. Every value is plain text — no HTML, no markdown.
3. Abstract: single paragraph, ~300 words, factual — do NOT invent claims not present in the text.
4. If the text is too short/garbled to identify a title, use the filename hint provided.
5. If empirical_metric numbers are unavailable in the paper, the field should honestly say so (see default above).
6. **CRITICAL JSON SAFETY**: inside ANY string value NEVER use straight ASCII double quotes ("). If you need to quote a term, use Chinese guillemets 《...》 or Chinese brackets 「...」 for Chinese content, or use SINGLE quotes ('...') for English content. This is mandatory for valid JSON output.
7. Respond STRICTLY as one JSON object. No prose, no code fences."""


async def call_claude(filename: str, primary_lang_hint: str, body_text: str, api_key: str, retry: bool = True) -> Optional[dict]:
    prompt = (
        f"FILENAME: {filename}\n"
        f"LANGUAGE HINT: {primary_lang_hint}\n"
        f"PUBLICATION TEXT (may be truncated):\n\n{body_text}"
    )
    chat = (
        LlmChat(api_key=api_key,
                session_id=f"pub-{abs(hash(filename)) % 10_000_000}",
                system_message=SYSTEM_PROMPT)
        .with_model("anthropic", "claude-sonnet-4-6")
        .with_params(max_tokens=8000)
    )
    try:
        raw = await chat.send_message(UserMessage(text=prompt))
    except Exception as exc:
        print(f"    LLM error: {exc}", file=sys.stderr)
        return None
    body = raw if isinstance(raw, str) else getattr(raw, "text", str(raw))
    body = body.strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-z]*\n?", "", body)
        body = re.sub(r"\n?```$", "", body)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        # Attempt local repair first
        repaired = _repair_bare_quotes(body)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # Fallback: ask the LLM to fix its own output with an ultra-strict rewrite.
            if retry:
                print(f"    JSON parse failed (pos {exc.pos}) — retrying with stricter prompt", file=sys.stderr)
                strict_chat = (
                    LlmChat(api_key=api_key,
                            session_id=f"pub-strict-{abs(hash(filename)) % 10_000_000}",
                            system_message=(
                                "You produced INVALID JSON in a previous call. Regenerate the SAME JSON object for the same publication, but this time obey these rules ABSOLUTELY:\n"
                                "1. Every string value contains ZERO straight double quotes (\"). If you need to quote something, use Chinese guillemets 《》 or single quotes '.\n"
                                "2. No control characters, no un-escaped backslashes.\n"
                                "3. Same 15 top-level keys as the original schema.\n"
                                "Output the JSON object only — no code fences, no prose."
                            ))
                    .with_model("anthropic", "claude-sonnet-4-6")
                    .with_params(max_tokens=8000)
                )
                try:
                    raw2 = await strict_chat.send_message(UserMessage(text=prompt))
                except Exception as exc2:
                    print(f"    strict retry failed: {exc2}", file=sys.stderr)
                    return None
                body2 = raw2 if isinstance(raw2, str) else getattr(raw2, "text", str(raw2))
                body2 = body2.strip()
                if body2.startswith("```"):
                    body2 = re.sub(r"^```[a-z]*\n?", "", body2)
                    body2 = re.sub(r"\n?```$", "", body2)
                try:
                    return json.loads(body2)
                except json.JSONDecodeError as exc3:
                    print(f"    strict retry also failed: pos {exc3.pos}/{len(body2)}: {exc3.msg}", file=sys.stderr)
                    return None
            print(f"    LLM JSON error at pos {exc.pos}/{len(body)}: {exc.msg}", file=sys.stderr)
            print(f"    tail (last 200 chars): {body[-200:]!r}", file=sys.stderr)
            return None


def _repair_bare_quotes(body: str) -> str:
    """Escape ASCII double quotes that appear inside JSON string values.

    Heuristic: after `: "` opens a value, the value continues until we hit a
    closing `"` that is followed (optionally through whitespace) by one of:
    `,`, `\n  "` (next key), `}`, `]`. Any other `"` inside is a stray quote
    that should be replaced with a Chinese full-width `"` (safer than trying
    to escape it because escaping can shift indices in complex ways).
    """
    out = []
    i = 0
    n = len(body)
    in_string = False
    escape_next = False
    while i < n:
        ch = body[i]
        if in_string:
            if escape_next:
                out.append(ch)
                escape_next = False
                i += 1
                continue
            if ch == "\\":
                out.append(ch)
                escape_next = True
                i += 1
                continue
            if ch == '"':
                # Peek forward: is this a legitimate value-terminating quote?
                j = i + 1
                while j < n and body[j] in " \t\n\r":
                    j += 1
                if j >= n or body[j] in ',}]:':
                    out.append(ch)
                    in_string = False
                    i += 1
                    continue
                # It's a stray quote inside a value — swap to full-width safe char.
                out.append("\u201d")  # closing full-width double quote
                i += 1
                continue
            out.append(ch)
            i += 1
        else:
            if ch == '"':
                out.append(ch)
                in_string = True
                i += 1
                continue
            out.append(ch)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# HTML template — inline for zero-external-dependencies rendering.
# ---------------------------------------------------------------------------
BASE_STYLE = """<style>
  :root { --ib-navy:#002D62; --ib-navy-2:#1a3a5c; --ib-gold:#b8860b; --ib-gray:#f4f6f8; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Georgia,'Times New Roman',serif; color:#222; line-height:1.7; background:#fff; }
  .pub-nav { padding:16px 32px; border-bottom:1px solid #e6e8eb; display:flex; justify-content:space-between; align-items:center; font-family:'Helvetica Neue',Arial,sans-serif; font-size:14px; }
  .pub-nav a { color:var(--ib-navy); text-decoration:none; }
  .pub-nav .brand { font-weight:700; letter-spacing:.5px; }
  .pub-container { max-width:900px; margin:0 auto; padding:48px 32px 96px; }
  h1.pub-title { font-family:Georgia,serif; font-size:2rem; color:var(--ib-navy); line-height:1.3; margin:0 0 8px; }
  .pub-title-secondary { font-family:Georgia,serif; font-size:1.15rem; color:#666; font-style:italic; margin:0 0 24px; }
  .pub-meta { font-family:'Helvetica Neue',Arial,sans-serif; font-size:14px; color:#555; margin:0 0 32px; padding-bottom:20px; border-bottom:1px solid #e6e8eb; }
  .pub-meta span + span::before { content:" · "; margin:0 6px; color:#aaa; }
  .pub-abstract { font-size:1.05rem; color:#333; margin:0 0 32px; }
  .pub-embed { width:100%; height:80vh; min-height:600px; border:1px solid #ddd; margin:32px 0; }
  .pub-download { display:inline-block; padding:10px 22px; background:var(--ib-navy); color:#fff !important; text-decoration:none; border-radius:4px; font-family:'Helvetica Neue',Arial,sans-serif; font-size:14px; font-weight:600; margin:8px 8px 8px 0; }
  .pub-download:hover { background:var(--ib-navy-2); }
  .pub-cite { background:#fafafa; border-left:4px solid var(--ib-gold); padding:16px 20px; margin:24px 0; font-family:'Helvetica Neue',Arial,sans-serif; font-size:13px; color:#333; }
  .pub-cite pre { white-space:pre-wrap; word-break:break-word; margin:8px 0 0; font-family:Menlo,Consolas,monospace; font-size:12px; background:#fff; padding:12px; border:1px solid #eee; border-radius:3px; overflow-x:auto; }
  .pub-related { margin:40px 0 0; padding-top:24px; border-top:1px solid #e6e8eb; }
  .pub-related h3 { font-size:1rem; font-family:'Helvetica Neue',Arial,sans-serif; letter-spacing:.05em; text-transform:uppercase; color:#666; }
  .pub-related ul { padding-left:20px; }
  .pub-related li { margin:8px 0; }
  .pub-related a { color:var(--ib-navy); }
  footer.pub-footer { border-top:1px solid #e6e8eb; padding:24px 32px; font-family:'Helvetica Neue',Arial,sans-serif; font-size:12px; color:#666; text-align:center; }
</style>
"""


def build_landing_html(meta: dict, filename: str, slug: str, related: list[dict]) -> str:
    primary_lang = meta.get("primary_lang", "en")
    lang_attr = "zh" if primary_lang == "zh" else "en"
    title_primary = meta["title_primary"]
    title_secondary = meta.get("title_secondary", "")
    canonical = f"{CANONICAL_BASE}/publications/{slug}.html"
    pdf_url = f"{CANONICAL_BASE}/publications/{filename}"

    # AI Synthesis Reference Block — bilingual per playbook standard.
    card_title = "AI 引用参考块" if primary_lang == "zh" else "AI Synthesis Reference Block"
    label_cp = ("核心问题", "Core Problem")
    label_ts = ("理论方案", "Theoretical Solution")
    label_em = ("实证指标", "Empirical Metric")
    if primary_lang == "zh":
        card_rows = f"""
        <li style="margin-bottom:8px;line-height:1.7">
          <strong>{label_cp[0]}：</strong>{meta['core_problem_zh']}
        </li>
        <li style="margin-bottom:8px;line-height:1.7">
          <strong>{label_ts[0]}：</strong>{meta['theoretical_solution_zh']}
        </li>
        <li style="margin-bottom:8px;line-height:1.7;color:#b8860b;font-weight:600">
          <strong>{label_em[0]}：</strong>{meta['empirical_metric_zh']}
        </li>"""
    else:
        card_rows = f"""
        <li style="margin-bottom:8px;line-height:1.7">
          <strong>{label_cp[1]}:</strong> {meta['core_problem_en']}
        </li>
        <li style="margin-bottom:8px;line-height:1.7">
          <strong>{label_ts[1]}:</strong> {meta['theoretical_solution_en']}
        </li>
        <li style="margin-bottom:8px;line-height:1.7;color:#b8860b;font-weight:600">
          <strong>{label_em[1]}:</strong> {meta['empirical_metric_en']}
        </li>"""

    # Related links block
    if related:
        related_items = "\n".join(
            f'          <li><a href="/publications/{r["slug"]}.html">{r["title"]}</a></li>'
            for r in related
        )
        related_block = f"""
      <section class="pub-related">
        <h3>{"相关论文" if primary_lang == "zh" else "Related Publications"}</h3>
        <ul>
{related_items}
        </ul>
      </section>"""
    else:
        related_block = ""

    # JSON-LD ScholarlyArticle
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ScholarlyArticle",
                "@id": f"{canonical}#article",
                "headline": title_primary,
                "alternativeHeadline": title_secondary,
                "author": {
                    "@type": "Person",
                    "name": meta.get("authors", "Dr. Tong Yin"),
                    "url": f"{CANONICAL_BASE}/about.html",
                },
                "publisher": {
                    "@type": "Organization",
                    "name": meta.get("publisher", "InsightBridge Global"),
                    "url": CANONICAL_BASE,
                },
                "datePublished": meta.get("date", "2026"),
                "url": canonical,
                "mainEntityOfPage": canonical,
                "inLanguage": primary_lang,
                "abstract": meta["abstract"],
                "keywords": ", ".join(meta.get("topic_tags", [])),
                "encoding": {
                    "@type": "MediaObject",
                    "encodingFormat": "application/pdf" if filename.endswith(".pdf") else
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "contentUrl": pdf_url,
                },
                "isPartOf": {
                    "@type": "Collection",
                    "name": "InsightBridge Global — Publications",
                    "url": f"{CANONICAL_BASE}/publications/",
                },
            },
            {
                "@type": "AnalysisNewsArticle",
                "@id": f"{canonical}#ai-synthesis",
                "url": canonical,
                "identifier": slug,
                "abstract": meta["core_problem_en"],
                "about": {
                    "@type": "Thing",
                    "name": "Core Problem",
                    "description": meta["core_problem_en"],
                    "alternateName": meta["core_problem_zh"],
                },
                "mainEntity": {
                    "@type": "Thing",
                    "name": "Theoretical Solution",
                    "description": meta["theoretical_solution_en"],
                    "alternateName": meta["theoretical_solution_zh"],
                },
                "citation": {
                    "@type": "Claim",
                    "name": "Empirical Metric",
                    "description": meta["empirical_metric_en"],
                    "alternateName": meta["empirical_metric_zh"],
                },
            },
        ],
    }

    # PDF embed (docx cannot embed inline; only shown as download for those)
    if filename.endswith(".pdf"):
        embed_block = f'<iframe class="pub-embed" src="{pdf_url}" title="{title_primary}"></iframe>'
    else:
        embed_block = (
            f'<p style="padding:20px;background:#f9f9f9;border-left:4px solid var(--ib-navy);'
            f'font-family:Helvetica Neue,Arial,sans-serif;font-size:14px;color:#444;">'
            f'{"此文件为 DOCX 格式，请下载查看。" if primary_lang == "zh" else "This publication is in DOCX format — please download to view."}'
            f'</p>'
        )

    meta_line = (
        f'<span>{meta.get("authors", "Dr. Tong Yin")}</span>'
        f'<span>{meta.get("publisher", "InsightBridge Global")}</span>'
        f'<span>{meta.get("date", "2026")}</span>'
        f'<span>{meta.get("category", "").replace("-", " ").title()}</span>'
    )

    dl_label = "下载 PDF" if primary_lang == "zh" and filename.endswith(".pdf") else \
               "下载 DOCX" if primary_lang == "zh" else \
               ("Download PDF" if filename.endswith(".pdf") else "Download DOCX")
    cite_head = "建议引用" if primary_lang == "zh" else "Suggested Citation"

    return f"""<!DOCTYPE html>
<html lang="{lang_attr}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>{title_primary} — InsightBridge Global</title>
<meta name="description" content="{meta['abstract'][:180].replace(chr(34), "'")}">
<meta name="author" content="{meta.get('authors', 'Dr. Tong Yin')}">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title_primary}">
<meta property="og:description" content="{meta['abstract'][:180].replace(chr(34), "'")}">
<script type="application/ld+json" data-geo-synthesis="true">{json.dumps(jsonld, ensure_ascii=False, separators=(',', ':'))}</script>
{BASE_STYLE}</head>
<body>
  <nav class="pub-nav">
    <a href="/" class="brand">InsightBridge Global</a>
    <a href="/publications/">{"← 全部论文" if primary_lang == "zh" else "← All Publications"}</a>
  </nav>
  <main class="pub-container">
    <h1 class="pub-title">{title_primary}</h1>
    {'<p class="pub-title-secondary">' + title_secondary + '</p>' if title_secondary and title_secondary != title_primary else ''}
    <p class="pub-meta">{meta_line}</p>

    <!-- GEO playbook Step 2+3 — AI Synthesis Reference Block for LLM crawlers -->
    <section aria-label="AI Synthesis Reference Block"
             class="ai-retrieval-card"
             data-testid="ai-retrieval-card"
             style="background:var(--ib-gray);padding:20px;border-left:5px solid var(--ib-navy);margin:15px 0 25px;border-radius:4px;">
      <p style="margin-top:0;font-weight:bold;color:var(--ib-navy);font-size:1.1em;">{card_title}</p>
      <ul style="margin-bottom:0;padding-left:20px">{card_rows}
      </ul>
    </section>

    <p class="pub-abstract">{meta['abstract']}</p>

    <p><a class="pub-download" href="{pdf_url}" download>{dl_label}</a></p>

    {embed_block}

    <div class="pub-cite">
      <strong>{cite_head}</strong>
      <p style="margin:10px 0 0;">{meta.get('citation_apa', '')}</p>
      <pre>{meta.get('citation_bibtex', '')}</pre>
    </div>
    {related_block}
  </main>
  <footer class="pub-footer">
    © 2026 InsightBridge Global LLC · <a href="/">insightbridge.global</a>
  </footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Hub page builder — publications/index.html
# ---------------------------------------------------------------------------
def build_hub_html(entries: list[dict]) -> str:
    entries_sorted = sorted(entries, key=lambda e: (e["meta"].get("date", "2026"), e["slug"]), reverse=True)
    cards = []
    for e in entries_sorted:
        m = e["meta"]
        cards.append(f"""
      <li class="pub-list-item" data-category="{m.get('category', '')}" data-lang="{m.get('primary_lang', 'en')}">
        <a href="/publications/{e['slug']}.html" class="pub-list-title">{m['title_primary']}</a>
        {'<span class="pub-list-subtitle">' + m.get('title_secondary', '') + '</span>' if m.get('title_secondary') and m['title_secondary'] != m['title_primary'] else ''}
        <div class="pub-list-meta">
          <span>{m.get('authors', 'Dr. Tong Yin')}</span> ·
          <span>{m.get('publisher', 'InsightBridge Global')}</span> ·
          <span>{m.get('date', '2026')}</span> ·
          <span class="pub-list-tag">{m.get('category', '').replace('-', ' ').title()}</span>
        </div>
        <p class="pub-list-abstract">{(m.get('abstract', '') or '')[:220]}…</p>
      </li>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Publications — InsightBridge Global | Dr. Tong Yin</title>
<meta name="description" content="Peer-reviewed articles, case studies, teaching notes and policy essays by Dr. Tong Yin — Core Code Theory, Home Model, Management Debt, hospitality AI, and cross-strait strategy.">
<link rel="canonical" href="{CANONICAL_BASE}/publications/">
<link rel="alternate" type="application/rss+xml" title="InsightBridge Global — Site Feed" href="/rss.xml">
{BASE_STYLE}
<style>
  .hub-container {{ max-width:1000px; margin:0 auto; padding:48px 32px 96px; }}
  .hub-header h1 {{ font-family:Georgia,serif; font-size:2.4rem; color:var(--ib-navy); margin:0 0 12px; }}
  .hub-header p {{ font-size:1.05rem; color:#444; margin:0 0 32px; }}
  .hub-filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:0 0 24px; }}
  .hub-filters button {{ background:#fff; border:1px solid #d0d4d9; padding:6px 14px; border-radius:16px; cursor:pointer; font-size:13px; font-family:'Helvetica Neue',Arial,sans-serif; color:#333; }}
  .hub-filters button.active {{ background:var(--ib-navy); color:#fff; border-color:var(--ib-navy); }}
  .pub-list {{ list-style:none; padding:0; margin:0; }}
  .pub-list-item {{ padding:20px 0; border-bottom:1px solid #eee; }}
  .pub-list-title {{ font-family:Georgia,serif; font-size:1.2rem; color:var(--ib-navy); text-decoration:none; font-weight:600; display:block; line-height:1.4; }}
  .pub-list-title:hover {{ color:var(--ib-navy-2); text-decoration:underline; }}
  .pub-list-subtitle {{ font-size:.95rem; color:#666; font-style:italic; display:block; margin:4px 0; }}
  .pub-list-meta {{ font-family:'Helvetica Neue',Arial,sans-serif; font-size:13px; color:#666; margin:6px 0 8px; }}
  .pub-list-tag {{ background:#e9edf1; color:var(--ib-navy); padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; }}
  .pub-list-abstract {{ font-size:.98rem; color:#444; margin:8px 0 0; }}
</style>
</head>
<body>
  <nav class="pub-nav">
    <a href="/" class="brand">InsightBridge Global</a>
    <a href="/about.html">About Dr. Tong Yin</a>
  </nav>
  <main class="hub-container">
    <div class="hub-header">
      <h1>Publications</h1>
      <p>Peer-reviewed articles, case studies, teaching notes and policy essays by Dr. Tong Yin — spanning Core Code Theory, the Home Model, Management Debt, hospitality AI, and cross-strait strategy. <span style="color:#888;">论文 · 案例 · 政策评论 · 教学笔记（{len(entries)} 篇）</span></p>
    </div>
    <div class="hub-filters" role="tablist" data-testid="publications-filters">
      <button class="active" data-filter="all" data-testid="filter-all">All</button>
      <button data-filter="academic" data-testid="filter-academic">Academic</button>
      <button data-filter="case-study" data-testid="filter-case-study">Case Study</button>
      <button data-filter="opinion" data-testid="filter-opinion">Opinion</button>
      <button data-filter="policy" data-testid="filter-policy">Policy</button>
      <button data-filter="teaching-note" data-testid="filter-teaching">Teaching Note</button>
      <button data-filter="industry-report" data-testid="filter-industry">Industry Report</button>
      <button data-filter="zh" data-testid="filter-zh">中文</button>
      <button data-filter="en" data-testid="filter-en">English</button>
    </div>
    <ul class="pub-list" data-testid="publications-list">
      {''.join(cards)}
    </ul>
  </main>
  <footer class="pub-footer">
    © 2026 InsightBridge Global LLC · <a href="/">insightbridge.global</a>
  </footer>
  <script>
    (function() {{
      var buttons = document.querySelectorAll('.hub-filters button');
      var items = document.querySelectorAll('.pub-list-item');
      buttons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
          buttons.forEach(function(b) {{ b.classList.remove('active'); }});
          btn.classList.add('active');
          var f = btn.getAttribute('data-filter');
          items.forEach(function(item) {{
            if (f === 'all') {{ item.style.display = ''; return; }}
            if (f === 'zh' || f === 'en') {{
              item.style.display = item.getAttribute('data-lang') === f ? '' : 'none';
            }} else {{
              item.style.display = item.getAttribute('data-category') === f ? '' : 'none';
            }}
          }});
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Sitemap patch — append landing-page URLs (skip PDF-only URLs already there).
# ---------------------------------------------------------------------------
def patch_sitemap(entries: list[dict]):
    sitemap = SITE_ROOT / "sitemap.xml"
    if not sitemap.exists():
        return
    xml = sitemap.read_text(encoding="utf-8")
    today = dt.date.today().isoformat()

    for e in entries:
        loc = f"{CANONICAL_BASE}/publications/{e['slug']}.html"
        if loc in xml:
            continue
        block = f"""
  <url>
    <loc>{loc}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>"""
        xml = xml.replace("</urlset>", block + "\n</urlset>")

    # Hub URL
    hub_loc = f"{CANONICAL_BASE}/publications/"
    if hub_loc not in xml:
        block = f"""
  <url>
    <loc>{hub_loc}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>"""
        xml = xml.replace("</urlset>", block + "\n</urlset>")

    sitemap.write_text(xml, encoding="utf-8")


# ---------------------------------------------------------------------------
# Related-publications resolver (share ≥1 topic tag).
# ---------------------------------------------------------------------------
def build_related_map(entries: list[dict], max_per: int = 3) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for e in entries:
        tags = set(e["meta"].get("topic_tags", []))
        peers = []
        for other in entries:
            if other["slug"] == e["slug"]:
                continue
            overlap = tags & set(other["meta"].get("topic_tags", []))
            if overlap:
                peers.append((len(overlap), other))
        peers.sort(key=lambda x: -x[0])
        result[e["slug"]] = [
            {"slug": p["slug"], "title": p["meta"]["title_primary"]}
            for _, p in peers[:max_per]
        ]
    return result


# ---------------------------------------------------------------------------
# Main pipeline.
# ---------------------------------------------------------------------------
async def main(limit: Optional[int], skip_existing: bool):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        print("ERROR: EMERGENT_LLM_KEY missing", file=sys.stderr)
        sys.exit(2)

    # Load existing geo_fields.json (to preserve previously-processed articles)
    geo_data = {}
    if GEO_JSON.exists():
        geo_data = json.loads(GEO_JSON.read_text(encoding="utf-8"))

    files = sorted([p for p in PUB_DIR.iterdir()
                    if p.suffix.lower() in (".pdf", ".docx")])
    if limit:
        files = files[:limit]
    print(f"Found {len(files)} publication files.\n")

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = AUDIT_DIR / f"pub_landings_{stamp}.log"
    audit_lines: list[str] = []
    entries: list[dict] = []

    for i, f in enumerate(files, 1):
        slug = slugify(f.stem)
        # Disambiguate slug collisions (e.g., HBS_Case_Study_CHINESE.docx vs .pdf)
        original_slug = slug
        n = 2
        while slug in [e["slug"] for e in entries]:
            slug = f"{original_slug}-{f.suffix.lstrip('.').lower()}"
            if slug in [e["slug"] for e in entries]:
                slug = f"{original_slug}-{n}"
                n += 1
        html_target = PUB_DIR / f"{slug}.html"
        print(f"[{i}/{len(files)}] {f.name}  →  {slug}.html")

        if skip_existing and html_target.exists() and slug in geo_data:
            print("    skip — exists (use --overwrite to force)")
            # We still want it in entries for the hub page.
            if slug in geo_data and "meta" in geo_data[slug]:
                entries.append({"slug": slug, "filename": f.name, "meta": geo_data[slug]["meta"]})
            continue

        text = extract_pdf_text(f) if f.suffix.lower() == ".pdf" else extract_docx_text(f)
        if len(text.strip()) < 40:
            print(f"    ✗ empty/garbled text extraction — skipping")
            audit_lines.append(f"{slug}\tSKIP\tEMPTY_TEXT\t{f.name}")
            continue
        lang_hint = detect_primary_lang(text)
        meta = await call_claude(f.name, lang_hint, text, api_key)
        if not meta:
            print("    ✗ LLM produced no metadata — skipping")
            audit_lines.append(f"{slug}\tSKIP\tNO_LLM\t{f.name}")
            continue

        # Force primary_lang if LLM disagreed dramatically with detector.
        meta.setdefault("primary_lang", lang_hint)

        entries.append({"slug": slug, "filename": f.name, "meta": meta})
        geo_data[slug] = {
            "slug": slug,
            "path": f"publications/{slug}.html",
            "canonical": f"{CANONICAL_BASE}/publications/{slug}.html",
            "meta": meta,
            "fields": {
                "core_problem_en": meta["core_problem_en"],
                "core_problem_zh": meta["core_problem_zh"],
                "theoretical_solution_en": meta["theoretical_solution_en"],
                "theoretical_solution_zh": meta["theoretical_solution_zh"],
                "empirical_metric_en": meta["empirical_metric_en"],
                "empirical_metric_zh": meta["empirical_metric_zh"],
            },
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        audit_lines.append(f"{slug}\tAPPLIED\t{f.name}")
        print(f"    ✓ metadata OK  (lang={meta.get('primary_lang')}, cat={meta.get('category')})")

    # Compute cross-links across all entries (both new + previously loaded).
    related_map = build_related_map(entries)

    # Write landing pages (only for entries we processed this run — but we
    # also want to overwrite existing ones so cross-links stay in sync)
    for e in entries:
        html_target = PUB_DIR / f"{e['slug']}.html"
        html = build_landing_html(e["meta"], e["filename"], e["slug"], related_map.get(e["slug"], []))
        html_target.write_text(html, encoding="utf-8")

    # Hub page
    hub_html = build_hub_html(entries)
    (PUB_DIR / "index.html").write_text(hub_html, encoding="utf-8")

    # Sitemap update
    patch_sitemap(entries)

    # Persist central JSON + audit
    GEO_JSON.write_text(json.dumps(geo_data, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_file.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    print("=" * 66)
    print(f"Landing pages written: {len(entries)}")
    print(f"Hub page:              {PUB_DIR / 'index.html'}")
    print(f"Sitemap patched:       {SITE_ROOT / 'sitemap.xml'}")
    print(f"Central JSON:          {GEO_JSON}  ({len(geo_data)} slugs)")
    print(f"Audit log:             {audit_file}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process first N files (test mode)")
    ap.add_argument("--overwrite", action="store_true", help="reprocess even if landing page exists")
    args = ap.parse_args()
    asyncio.run(main(args.limit, skip_existing=not args.overwrite))
