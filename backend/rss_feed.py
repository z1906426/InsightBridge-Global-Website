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
    """Reuse the existing publications extractor to include pub URLs
    in the feed. Best-effort — failures are non-fatal."""
    try:
        from publications import extract_publication_urls

        urls = extract_publication_urls()
    except Exception:
        logger.exception("rss_feed: could not extract publication URLs")
        return []

    items: List[Dict[str, str]] = []
    for url in urls:
        # Derive a human-readable title from the filename
        slug = url.rstrip("/").split("/")[-1]
        title = (
            slug.replace(".html", "")
            .replace(".pdf", " (PDF)")
            .replace(".docx", " (DOCX)")
            .replace("-", " ")
            .replace("_", " ")
            .strip()
            .title()
        )
        items.append(
            {
                "path": url.replace(SITE_URL, "") if url.startswith(SITE_URL) else url,
                "url": url if url.startswith("http") else f"{SITE_URL}{url}",
                "title": f"Publication — {title}",
                "description": (
                    "Research publication from InsightBridge Global's "
                    "Research & Publications catalogue."
                ),
                "category": "Publication",
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
