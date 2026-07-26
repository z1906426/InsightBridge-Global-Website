"""populate_geo_static.py — GEO 6-field enrichment for the static main site.

Adapts the InsightBridge Intelligence sister-site playbook (Step 2 + 3 + 4)
to a static HTML corporate site. For each of the 8 designated articles:

    * Extract EN/ZH body text (BeautifulSoup)
    * Call Claude Sonnet 4.6 (Emergent LLM key) with a strict prompt:
        - 3 fields (core problem, theoretical solution, empirical metric) × 2 langs
        - Every numeric claim MUST appear verbatim in the article body
        - Simplified Chinese only, single-line, no HTML
    * Inject a visible AI Synthesis Reference Block <section> right after the
      article's H1/subtitle (per-file anchor)
    * Append a JSON-LD <script> block to <head> describing the same 6 fields
    * Write a central /app/frontend/site/_data/geo_fields.json so the FastAPI
      `/api/articles/{slug}/ai-tldr` endpoint can serve the same data to
      LLM crawlers over the API surface

Direct-write mode per user directive (2026-02): no dry-run gate. Every write
is logged to /app/backend/_audit/geo_static_YYYYMMDD_HHMMSS.log for reversal.
"""

from __future__ import annotations

import asyncio
import copy
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, NavigableString
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

SITE_ROOT = Path("/app/frontend/site")
DATA_DIR = SITE_ROOT / "_data"
DATA_DIR.mkdir(exist_ok=True)
GEO_JSON = DATA_DIR / "geo_fields.json"

AUDIT_DIR = Path("/app/backend/_audit")
AUDIT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Article registry — 8 files with their insertion anchors + language config.
# ---------------------------------------------------------------------------
# lang_mode:
#   'bilingual_span' — page uses <span class="lang-en">…<span class="lang-cn">…
#   'zh_dominant'    — mostly Chinese with English H1/subtitle where present
#   'en_only'        — pure English (landing/ai-pricing)
#
# insert_after: regex matched against the raw HTML; card injected right after.
# ---------------------------------------------------------------------------
ARTICLES: list[dict] = [
    {
        "slug": "core-code-theory",
        "path": "theories/core-code-theory.html",
        "lang_mode": "bilingual_span",
        "insert_after": r'<p class="theory-subtitle">.*?</p>\s*',
    },
    {
        "slug": "ddrt",
        "path": "theories/ddrt.html",
        "lang_mode": "bilingual_span",
        "insert_after": r'<p class="theory-subtitle">.*?</p>\s*',
    },
    {
        "slug": "home-model",
        "path": "theories/home-model.html",
        "lang_mode": "bilingual_span",
        "insert_after": r'<p class="theory-subtitle">.*?</p>\s*',
    },
    {
        "slug": "management-debt",
        "path": "theories/management-debt.html",
        "lang_mode": "bilingual_span",
        "insert_after": r'<p class="theory-subtitle">.*?</p>\s*',
    },
    {
        "slug": "xian-incident-republican-china-politics",
        "path": "publications/xian-incident-republican-china-politics.html",
        "lang_mode": "zh_dominant",
        # Insert after first <h1> in the article body.
        "insert_after": r'<h1[^>]*>.*?</h1>\s*',
    },
    {
        "slug": "intelligence-market-report",
        "path": "intelligence-market-report.html",
        "lang_mode": "bilingual_span",
        # Insert after the ZH cover title h1.
        "insert_after": r'<h1 class="cover-title-zh">.*?</h1>\s*',
    },
    {
        "slug": "intelligence-vol01",
        "path": "intelligence-vol01.html",
        "lang_mode": "bilingual_span",
        "insert_after": r'<h1 class="title-zh">.*?</h1>\s*',
    },
    {
        "slug": "ai-pricing",
        "path": "landing/ai-pricing.html",
        "lang_mode": "en_only",
        "insert_after": r'<h1>.*?</h1>\s*',
    },
]

# ---------------------------------------------------------------------------
# LLM prompt (mirrors sister-site playbook constraints).
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are generating GEO (Generative Engine Optimization) synthesis fields for Dr. Tong Yin's InsightBridge Global articles.

For each article you will produce EXACTLY 6 fields, one JSON object:

{
  "core_problem_en":           "<single sentence — the article's central diagnostic question>",
  "core_problem_zh":           "<same, simplified Chinese>",
  "theoretical_solution_en":   "<single sentence — the framework/mechanism the article proposes>",
  "theoretical_solution_zh":   "<same, simplified Chinese>",
  "empirical_metric_en":       "<single sentence containing at least one number from the article body verbatim (percent, absolute, or delta)>",
  "empirical_metric_zh":       "<same, simplified Chinese, same number verbatim>"
}

HARD RULES:
1. Every numeric claim in *empirical_metric_en/zh* MUST appear verbatim in the article body (percent, currency, count, or range). Do NOT fabricate statistics.
2. Chinese output MUST be simplified Chinese (简体中文). No traditional characters.
3. Each value is a single line — NO line breaks, NO HTML tags, NO markdown.
4. Values are complete sentences ending with a period (English) or 。 (Chinese).
5. Terminology: prefer these framework names where relevant — Core Code Theory / Home Model / Management Debt / DDRT / Polaris / Orion / Nova / hospitality / pricing.
6. English max 30 words per field. Chinese max 60 characters per field.

Respond STRICTLY as one JSON object. No prose, no code fences, no comments."""


def extract_plain_text(soup: BeautifulSoup, mode: str) -> tuple[str, str]:
    """Return (english_text, chinese_text) plain strings from the article body.

    * bilingual_span: split on .lang-en / .lang-cn spans.
    * zh_dominant: all article text goes into chinese_text.
    * en_only: all article text goes into english_text.
    """
    for tag in soup.select("script, style, nav, header, footer, aside"):
        tag.decompose()
    body = soup.find("article") or soup.find("main") or soup.body or soup

    if mode == "bilingual_span":
        en_parts, zh_parts = [], []
        for el in body.find_all(class_="lang-en"):
            en_parts.append(el.get_text(" ", strip=True))
        for el in body.find_all(class_="lang-cn"):
            zh_parts.append(el.get_text(" ", strip=True))
        # Fallback: if no split spans exist, dump full text into both.
        if not en_parts and not zh_parts:
            txt = body.get_text(" ", strip=True)
            return txt, txt
        return " ".join(en_parts), " ".join(zh_parts)

    if mode == "zh_dominant":
        return "", body.get_text(" ", strip=True)

    if mode == "en_only":
        return body.get_text(" ", strip=True), ""

    return body.get_text(" ", strip=True), ""


NUMBER_RE = re.compile(
    r"""
    (?:\$|USD\s?|¥|人民币\s?)?      # optional currency prefix
    \d{1,3}(?:[,，]\d{3})*(?:\.\d+)? # 1,234.56 or 12.5
    \s?
    (?:%|％|pp|bp|bps|K|M|B|亿|万|千|倍|人|篇|个|国家?)?  # optional unit
    """,
    re.VERBOSE,
)


def find_numbers(text: str) -> set[str]:
    return {m.strip() for m in NUMBER_RE.findall(text or "") if m.strip()}


def verbatim_numbers_present(claim: str, article_text: str) -> bool:
    """A permissive check — the claim must share at least one numeric token with
    the article body (percent, absolute, or delta). Accepts fuzzy match on
    whitespace and Chinese/full-width comma variants."""
    if not article_text:
        return True  # nothing to verify against, permit
    claim_nums = find_numbers(claim)
    if not claim_nums:
        return True  # LLM omitted numbers entirely — permit but flag downstream
    article_norm = article_text.replace("，", ",")
    return any(n.replace("，", ",") in article_norm for n in claim_nums)


def is_simplified_chinese(text: str) -> bool:
    """Very light check — reject if any of the top-frequency traditional-only
    characters appear. Full validation is out-of-scope; this catches obvious
    lapses like 為/繁/體/發/國."""
    if not text:
        return True
    trad_hits = re.findall(r"[為繁體發國體實現時對經濟從]", text)
    return len(trad_hits) == 0


# ---------------------------------------------------------------------------
# LLM invocation.
# ---------------------------------------------------------------------------
async def call_claude(en_text: str, zh_text: str, api_key: str) -> Optional[dict]:
    prompt_body = (
        f"ARTICLE — ENGLISH BODY (excerpt, up to 4000 chars):\n"
        f"{en_text[:4000] or '(no English content — infer from Chinese)'}\n\n"
        f"ARTICLE — CHINESE BODY (excerpt, up to 4000 chars):\n"
        f"{zh_text[:4000] or '(no Chinese content — mirror the English)'}\n"
    )
    chat = (
        LlmChat(api_key=api_key,
                session_id=f"geo-static-{abs(hash(en_text[:200] + zh_text[:200])) % 10_000_000}",
                system_message=SYSTEM_PROMPT)
        .with_model("anthropic", "claude-sonnet-4-6")
    )
    try:
        raw = await chat.send_message(UserMessage(text=prompt_body))
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
    except json.JSONDecodeError:
        print(f"    LLM returned non-JSON: {body[:120]!r}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# HTML card + JSON-LD generation.
# ---------------------------------------------------------------------------
def build_card_html(fields: dict, lang_mode: str) -> str:
    def _row(label_en: str, label_zh: str, val_en: str, val_zh: str, highlight: bool = False):
        val_style = ";color:#b8860b;font-weight:600" if highlight else ""
        if lang_mode == "bilingual_span":
            return (
                f'      <li style="margin-bottom:8px">\n'
                f'        <strong>{label_en}:</strong>\n'
                f'        <span class="lang-en" style="line-height:1.6{val_style}">{val_en}</span>\n'
                f'        <span class="lang-cn" style="line-height:1.6{val_style}">{val_zh}</span>\n'
                f'      </li>'
            )
        if lang_mode == "zh_dominant":
            return (
                f'      <li style="margin-bottom:8px;line-height:1.7{val_style}">\n'
                f'        <strong>{label_zh}：</strong>{val_zh}\n'
                f'      </li>'
            )
        return (
            f'      <li style="margin-bottom:8px;line-height:1.7{val_style}">\n'
            f'        <strong>{label_en}:</strong> {val_en}\n'
            f'      </li>'
        )

    rows = "\n".join([
        _row("Core Problem", "核心问题",
             fields["core_problem_en"], fields["core_problem_zh"]),
        _row("Theoretical Solution", "理论方案",
             fields["theoretical_solution_en"], fields["theoretical_solution_zh"]),
        _row("Empirical Metric", "实证指标",
             fields["empirical_metric_en"], fields["empirical_metric_zh"],
             highlight=True),
    ])

    title = (
        'AI Synthesis Reference Block'
        if lang_mode != "zh_dominant"
        else 'AI 引用参考块'
    )
    return (
        '\n  <!-- GEO playbook Step 2+3 — AI Synthesis Reference Block\n'
        '       6-field synthesis card for LLM crawlers (Core Problem / Theoretical Solution\n'
        '       / Empirical Metric × EN+ZH). SSR-rendered so GPTBot/ClaudeBot/PerplexityBot\n'
        '       see the fields in raw HTML. Generated by /app/backend/populate_geo_static.py -->\n'
        '  <section aria-label="AI Synthesis Reference Block"\n'
        '           class="ai-retrieval-card"\n'
        '           data-testid="ai-retrieval-card"\n'
        '           style="background:#f4f6f8;padding:20px;border-left:5px solid #002D62;margin:15px 0 25px;border-radius:4px;">\n'
        '    <p style="margin-top:0;font-weight:bold;color:#002D62;font-size:1.1em;">\n'
        f'      {title}\n'
        '    </p>\n'
        '    <ul style="margin-bottom:0;padding-left:20px">\n'
        f'{rows}\n'
        '    </ul>\n'
        '  </section>\n'
    )


def build_jsonld_block(slug: str, fields: dict, canonical_url: str) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "AnalysisNewsArticle",
        "@id": f"{canonical_url}#ai-synthesis",
        "url": canonical_url,
        "identifier": slug,
        "abstract": fields["core_problem_en"],
        "about": {
            "@type": "Thing",
            "name": "Core Problem",
            "description": fields["core_problem_en"],
            "alternateName": fields["core_problem_zh"],
        },
        "mainEntity": {
            "@type": "Thing",
            "name": "Theoretical Solution",
            "description": fields["theoretical_solution_en"],
            "alternateName": fields["theoretical_solution_zh"],
        },
        "citation": {
            "@type": "Claim",
            "name": "Empirical Metric",
            "description": fields["empirical_metric_en"],
            "alternateName": fields["empirical_metric_zh"],
        },
    }
    return (
        '\n<!-- GEO playbook Step 2 — AI synthesis JSON-LD (structured data for LLM crawlers) -->\n'
        '<script type="application/ld+json" data-geo-synthesis="true">'
        + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        + '</script>\n'
    )


# ---------------------------------------------------------------------------
# HTML in-place mutation helpers.
# ---------------------------------------------------------------------------
CARD_SENTINEL = 'data-testid="ai-retrieval-card"'
JSONLD_SENTINEL = 'data-geo-synthesis="true"'


def inject_card(html: str, anchor_regex: str, card: str) -> tuple[str, bool]:
    if CARD_SENTINEL in html:
        # Replace existing card (idempotent overwrite).
        html = re.sub(
            r'\n?  <!-- GEO playbook Step 2\+3.*?</section>\n?',
            '',
            html,
            count=1,
            flags=re.DOTALL,
        )
    m = re.search(anchor_regex, html, re.DOTALL)
    if not m:
        return html, False
    idx = m.end()
    return html[:idx] + card + html[idx:], True


def inject_jsonld(html: str, block: str) -> str:
    if JSONLD_SENTINEL in html:
        html = re.sub(
            r'\n<!-- GEO playbook Step 2.*?data-geo-synthesis="true">.*?</script>\n',
            '',
            html,
            count=1,
            flags=re.DOTALL,
        )
    # Insert right before </head>.
    return re.sub(r'</head>', block + '</head>', html, count=1)


def canonical_of(html: str) -> str:
    m = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', html)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Main pipeline.
# ---------------------------------------------------------------------------
async def process_article(art: dict, api_key: str, existing_data: dict, audit_lines: list) -> Optional[dict]:
    path = SITE_ROOT / art["path"]
    if not path.exists():
        print(f"  ✗ missing file: {path}")
        return None
    raw = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "lxml")
    en_text, zh_text = extract_plain_text(copy.copy(soup), art["lang_mode"])

    print(f"  extracted {len(en_text)} en chars / {len(zh_text)} zh chars")

    fields = await call_claude(en_text, zh_text, api_key)
    if not fields:
        audit_lines.append(f"{art['slug']}\tSKIP\tLLM_NO_OUTPUT")
        return None

    required = ("core_problem_en", "core_problem_zh",
                "theoretical_solution_en", "theoretical_solution_zh",
                "empirical_metric_en", "empirical_metric_zh")
    if not all(fields.get(k) for k in required):
        audit_lines.append(f"{art['slug']}\tSKIP\tMISSING_FIELDS\t{list(fields.keys())}")
        print(f"  ✗ missing required fields")
        return None

    if not verbatim_numbers_present(fields["empirical_metric_en"], en_text):
        audit_lines.append(f"{art['slug']}\tWARN\tEN_NUMBER_NOT_VERBATIM\t{fields['empirical_metric_en']}")
        print(f"  ⚠ EN empirical metric number not found verbatim in body")
    if not verbatim_numbers_present(fields["empirical_metric_zh"], zh_text or en_text):
        audit_lines.append(f"{art['slug']}\tWARN\tZH_NUMBER_NOT_VERBATIM\t{fields['empirical_metric_zh']}")
        print(f"  ⚠ ZH empirical metric number not found verbatim in body")
    if not is_simplified_chinese(fields["core_problem_zh"] + fields["theoretical_solution_zh"] + fields["empirical_metric_zh"]):
        audit_lines.append(f"{art['slug']}\tWARN\tTRADITIONAL_CHINESE_DETECTED")
        print(f"  ⚠ traditional-Chinese hits detected in ZH fields")

    # Build HTML mutations.
    canonical = canonical_of(raw) or f"https://insightbridge.global/{art['path']}"
    card = build_card_html(fields, art["lang_mode"])
    jsonld = build_jsonld_block(art["slug"], fields, canonical)

    new_html, injected = inject_card(raw, art["insert_after"], card)
    if not injected:
        audit_lines.append(f"{art['slug']}\tSKIP\tANCHOR_NOT_FOUND\t{art['insert_after']}")
        print(f"  ✗ anchor regex not found — skipping HTML mutation")
        return None
    new_html = inject_jsonld(new_html, jsonld)
    path.write_text(new_html, encoding="utf-8")
    audit_lines.append(f"{art['slug']}\tAPPLIED\t{canonical}")
    print(f"  ✓ card + JSON-LD injected → {path.relative_to(SITE_ROOT)}")

    existing_data[art["slug"]] = {
        "slug": art["slug"],
        "path": art["path"],
        "canonical": canonical,
        "fields": fields,
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    return fields


async def main():
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        print("ERROR: EMERGENT_LLM_KEY not in env", file=sys.stderr)
        sys.exit(2)

    existing = {}
    if GEO_JSON.exists():
        existing = json.loads(GEO_JSON.read_text(encoding="utf-8"))

    audit_lines = []
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = AUDIT_DIR / f"geo_static_{stamp}.log"

    print(f"Populating GEO fields for {len(ARTICLES)} static articles ...\n")
    for i, art in enumerate(ARTICLES, 1):
        print(f"[{i}/{len(ARTICLES)}] {art['slug']}  ({art['path']})")
        await process_article(art, api_key, existing, audit_lines)
        print()

    GEO_JSON.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    audit_file.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")
    print("=" * 66)
    print(f"Central JSON: {GEO_JSON}  ({len(existing)} slugs)")
    print(f"Audit log:    {audit_file}")


if __name__ == "__main__":
    asyncio.run(main())
