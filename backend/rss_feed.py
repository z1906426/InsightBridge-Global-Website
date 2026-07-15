"""
RSS 2.0 feed generator for the main site (insightbridge.global).

Purpose:
  Publish a machine-readable feed of the main site's section URLs so that
  search-engine crawlers (Google, Bing, Baidu, Yandex, etc.) can rediscover
  and re-crawl every canonical page on their own schedule — reducing our
  reliance on manual ping/push APIs alone.

Scope:
  - Only MAIN site sections (homepage EN/ZH, tools, market report,
    intelligence vol.01, privacy) + auto-extracted publications.
  - Sister-site articles are NOT included here — the sister site publishes
    its own RSS feed for those.

Output:
  A static file written to `/app/frontend/site/rss.xml`, served publicly
  at https://insightbridge.global/rss.xml. Regenerated once every 24 h by
  APScheduler, and on backend startup if the file is missing.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import List, Dict
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "insightbridge.global")
SITE_URL = f"https://{SITE_DOMAIN}"

RSS_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "frontend" / "site" / "rss.xml"
)

# Canonical section list — matches sitemap.xml priorities.
# Order = display order in the feed.
SECTIONS: List[Dict[str, str]] = [
    {
        "path": "/",
        "title": "InsightBridge Global — Strategy & AI Research",
        "description": (
            "Homepage of InsightBridge Global LLC — founded by Dr. Tong Yin. "
            "Covenant-based strategic management, POLARIS pricing, NOVA "
            "distribution economics, and applied AI research for global "
            "hospitality and tourism."
        ),
        "category": "Homepage",
    },
    {
        "path": "/zh.html",
        "title": "InsightBridge Global — 战略咨询与 AI 研究(中文)",
        "description": (
            "InsightBridge Global LLC 中文主页 —— 汤颖博士创立。契约式战略"
            "管理、POLARIS 定价模型、NOVA 分销经济学,以及面向全球旅游酒店"
            "业的应用 AI 研究。"
        ),
        "category": "Homepage / 中文",
    },
    {
        "path": "/about.html",
        "title": "Dr. Tong Yin — Executive Biography | InsightBridge Global",
        "description": (
            "Executive biography of Dr. Tong Yin — Founder & CEO of "
            "InsightBridge Global LLC. Ph.D., Hospitality Management "
            "(Auburn); originator of The Home Model, Management Debt, "
            "DDRT and Core Code Theory."
        ),
        "category": "About",
    },
    {
        "path": "/theories/",
        "title": "Strategic Management Theories — Dr. Tong Yin",
        "description": (
            "Original strategic-management frameworks by Dr. Tong Yin: "
            "Core Code Theory, The Home Model, Management Debt, and "
            "Dynamic Driver Replacement Theory."
        ),
        "category": "Theories",
    },
    {
        "path": "/theories/core-code-theory.html",
        "title": "Core Code Theory (CCT) — Strategic Management Framework",
        "description": (
            "Core Code Theory (CCT) — a framework by Dr. Tong Yin for "
            "identifying the foundational structural code of any organisation."
        ),
        "category": "Theory / CCT",
    },
    {
        "path": "/theories/home-model.html",
        "title": "The Home Model — Covenant-Based Governance Framework",
        "description": (
            "The Home Model — a covenant-based governance framework "
            "grounded in human-centric traits AI cannot replicate."
        ),
        "category": "Theory / Home Model",
    },
    {
        "path": "/theories/management-debt.html",
        "title": "Management Debt — Diagnosing Structural Organisational Decline",
        "description": (
            "Management Debt — a balance-sheet-style framework for "
            "diagnosing structural organisational decline before it "
            "becomes irreversible."
        ),
        "category": "Theory / Management Debt",
    },
    {
        "path": "/theories/ddrt.html",
        "title": "Dynamic Driver Replacement Theory (DDRT)",
        "description": (
            "Dynamic Driver Replacement Theory (DDRT) — modelling how "
            "organisations replace declining growth drivers with new "
            "ones without losing structural stability."
        ),
        "category": "Theory / DDRT",
    },
    {
        "path": "/media/yin-vision-2030-predictions-vs-reality-bilingual-archive.pdf",
        "title": "Saudi Vision 2030 — Predictions vs. Market Reality (Bilingual Archive)",
        "description": (
            "Longitudinal archive placing six years of Dr. Yin's published "
            "forecasts on Saudi ultra-luxury tourism and sovereign-fund "
            "strategy alongside verifiable 2026 market data. Bilingual "
            "EN/中文 timestamped PDF."
        ),
        "category": "Featured Archive",
    },
    {
        "path": "/tools.html",
        "title": "POLARIS Pricing & NOVA Distribution Calculators",
        "description": (
            "Interactive server-side calculators: POLARIS (5-driver strategic "
            "rate positioning) and NOVA (true landed cost across the OTA fee "
            "stack). Formulas are IP-protected and executed on the backend."
        ),
        "category": "Interactive Tools",
    },
    {
        "path": "/intelligence-market-report.html",
        "title": "Intelligence Market Report — Long-form Analysis",
        "description": (
            "Long-form intelligence report — market dynamics, distribution "
            "cost structures, and covenant-based governance case studies for "
            "hospitality and tourism operators."
        ),
        "category": "Research",
    },
    {
        "path": "/intelligence-vol01.html",
        "title": "Intelligence Vol. 01 — Founder Brief",
        "description": (
            "Volume 01 of the InsightBridge Intelligence series — founder's "
            "brief on structural intelligence, crisis-mode governance, and "
            "the Home Model framework."
        ),
        "category": "Research",
    },
    {
        "path": "/privacy.html",
        "title": "Privacy Policy — InsightBridge Global LLC",
        "description": "Privacy policy and data-handling disclosures.",
        "category": "Policy",
    },
]


def _rfc822(dt: datetime) -> str:
    """Format datetime as RFC-822 (RSS 2.0 spec)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def _extract_publications() -> List[Dict[str, str]]:
    """Extract article/paper URLs from ALL research-bearing sections of
    index.html — Publications, Intelligence (press coverage), Cases, and
    the featured 2027 whitepaper referenced in the trust strip.

    For each URL, tries to recover the human-readable title from the
    nearest preceding <h1>-<h6> heading (or falls back to a slug-derived
    title if none is found).

    Best-effort — failures are non-fatal.
    """
    import html as html_lib
    import re
    from urllib.parse import urljoin

    index_path = (
        Path(__file__).resolve().parent.parent / "frontend" / "site" / "index.html"
    )
    if not index_path.exists():
        return []

    try:
        html = index_path.read_text(encoding="utf-8")
    except Exception:
        logger.exception("rss_feed: could not read index.html")
        return []

    # Sections we care about — everything under Research & Publications
    # plus the Intelligence Coverage strip that lists press articles.
    section_ids = {
        "page-publications": "Publication",
        "page-intelligence": "Intelligence Coverage",
        "cited-worldwide-strip": "Featured Whitepaper",
    }

    # Locate all section start positions, so we can carve blocks
    matches = list(re.finditer(r'<section[^>]*id="([^"]+)"', html))
    boundaries = [(m.group(1), m.start()) for m in matches] + [("__END__", len(html))]

    site_base = f"{SITE_URL}/"
    seen: set[str] = set()
    items: List[Dict[str, str]] = []

    # Already-covered top-level pages — don't duplicate them as "publications".
    section_paths = {s["path"].lstrip("/") for s in SECTIONS}
    section_paths.add("index.html")

    href_re = re.compile(r'href="([^"]+\.(?:pdf|docx|html))"', re.IGNORECASE)
    heading_re = re.compile(r'<h[1-6][^>]*>(.+?)</h[1-6]>', re.DOTALL | re.IGNORECASE)
    tag_re = re.compile(r'<[^>]+>')

    def _title_for(pos_in_html: int, fallback_slug: str) -> str:
        """Return the nearest preceding <h1>-<h6> text; fall back to slug."""
        window = html[max(0, pos_in_html - 2500):pos_in_html]
        heads = heading_re.findall(window)
        for raw in reversed(heads):
            clean = tag_re.sub("", raw)
            # Unescape any HTML entities so downstream XML escape produces
            # a single, correct escape pass.
            clean = html_lib.unescape(clean)
            # Some cards contain "EN Title\n         中文标题" — take first non-empty line
            first_line = next((ln.strip() for ln in clean.split("\n") if ln.strip()), "")
            if len(first_line) >= 4:
                return first_line[:180]
        # Slug fallback
        return (
            fallback_slug.replace(".html", "")
            .replace(".pdf", " (PDF)")
            .replace(".docx", " (DOCX)")
            .replace("-", " ")
            .replace("_", " ")
            .strip()
            .title()[:180]
        )

    for i, (sid, start) in enumerate(boundaries[:-1]):
        if sid not in section_ids:
            continue
        end = boundaries[i + 1][1]
        block = html[start:end]

        for m in href_re.finditer(block):
            href = m.group(1).strip()
            low = href.lower()
            if (
                href.startswith("#")
                or href.startswith("mailto:")
                or "linkedin.com" in low
                or "javascript:" in low
                or "hotelnewsresource.com" in low       # external press site
                or "intelligence.insightbridge" in low   # sister-site handles its own RSS
            ):
                continue

            # Normalise to absolute same-host URL only
            if href.startswith("http://") or href.startswith("https://"):
                if SITE_DOMAIN not in href:
                    continue
                url = href
            else:
                url = urljoin(site_base, href.lstrip("/"))

            # Skip already-covered section pages
            rel = url.replace(SITE_URL + "/", "").lstrip("/")
            if rel in section_paths or f"/{rel}" in section_paths:
                continue

            if url in seen:
                continue
            seen.add(url)

            slug = url.rstrip("/").split("/")[-1]
            abs_pos = start + m.start()
            title = _title_for(abs_pos, slug)

            items.append(
                {
                    "path": url.replace(SITE_URL, ""),
                    "url": url,
                    "title": f"{section_ids[sid]} — {title}",
                    "description": (
                        "Research publication and press coverage from "
                        "InsightBridge Global — strategy, AI hospitality, "
                        "and covenant-based governance."
                    ),
                    "category": section_ids[sid],
                }
            )
    return items


def build_rss_xml() -> str:
    """Build a valid RSS 2.0 XML document for the main site."""
    now = datetime.now(timezone.utc)
    build_date = _rfc822(now)

    items_xml_parts: List[str] = []

    for s in SECTIONS:
        loc = f"{SITE_URL}{s['path']}"
        items_xml_parts.append(
            "    <item>\n"
            f"      <title>{escape(s['title'])}</title>\n"
            f"      <link>{escape(loc)}</link>\n"
            f"      <guid isPermaLink=\"true\">{escape(loc)}</guid>\n"
            f"      <description>{escape(s['description'])}</description>\n"
            f"      <category>{escape(s['category'])}</category>\n"
            f"      <pubDate>{build_date}</pubDate>\n"
            "    </item>"
        )

    for p in _extract_publications():
        loc = p["url"]
        items_xml_parts.append(
            "    <item>\n"
            f"      <title>{escape(p['title'])}</title>\n"
            f"      <link>{escape(loc)}</link>\n"
            f"      <guid isPermaLink=\"true\">{escape(loc)}</guid>\n"
            f"      <description>{escape(p['description'])}</description>\n"
            f"      <category>{escape(p['category'])}</category>\n"
            f"      <pubDate>{build_date}</pubDate>\n"
            "    </item>"
        )

    items_xml = "\n".join(items_xml_parts)

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"\n'
        '     xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        "    <title>InsightBridge Global — Site Feed</title>\n"
        f"    <link>{SITE_URL}/</link>\n"
        f'    <atom:link href="{SITE_URL}/rss.xml" rel="self" type="application/rss+xml" />\n'
        "    <description>Canonical section feed for InsightBridge Global — "
        "strategy consulting, POLARIS/NOVA calculators, applied AI research "
        "and publications. Published for crawler discovery.</description>\n"
        "    <language>en-US</language>\n"
        "    <copyright>© InsightBridge Global LLC</copyright>\n"
        f"    <lastBuildDate>{build_date}</lastBuildDate>\n"
        f"    <pubDate>{build_date}</pubDate>\n"
        "    <ttl>1440</ttl>\n"
        f"{items_xml}\n"
        "  </channel>\n"
        "</rss>\n"
    )
    return xml


def write_rss(path: Path = RSS_OUTPUT_PATH) -> Dict[str, object]:
    """Generate the feed and write it to disk atomically."""
    xml = build_rss_xml()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(xml, encoding="utf-8")
    tmp.replace(path)
    logger.info("rss_feed: wrote %s (%d bytes)", path, len(xml))
    return {
        "ok": True,
        "path": str(path),
        "url": f"{SITE_URL}/rss.xml",
        "bytes": len(xml),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def ensure_rss_exists(path: Path = RSS_OUTPUT_PATH) -> None:
    """Called on backend startup. Generates the feed if it's missing."""
    if not path.exists():
        try:
            write_rss(path)
        except Exception:
            logger.exception("rss_feed: initial generation failed")
