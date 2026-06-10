"""
Sister-site article fetcher — pulls latest articles from
intelligence.insightbridge.global and exposes them for:
  1. /api/headlines    → main-site hero brief sidebar
  2. seo_push.py       → automatic submission to search engines

Refreshes every 6 hours via APScheduler.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

SISTER_DOMAIN = "intelligence.insightbridge.global"
SISTER_BASE = f"https://{SISTER_DOMAIN}"
SISTER_SITEMAP = f"{SISTER_BASE}/sitemap.xml"

REFRESH_INTERVAL_HOURS = 6
ARTICLES_FOR_BRIEF = 7      # how many to show on main site hero
ARTICLES_FOR_SEO_PUSH = 4   # newest 4 included in SEO push (keeps Baidu 10/day quota)


# ============================================================
#  Sitemap parsing
# ============================================================

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _fetch_sister_sitemap_articles() -> List[Dict[str, Any]]:
    """
    Returns a list of article entries from the sister-site sitemap.
    Each entry: {loc, lastmod (datetime|None)}
    Only URLs under /articles/ are returned (categories/system pages filtered out).
    """
    resp = requests.get(SISTER_SITEMAP, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    out: List[Dict[str, Any]] = []
    for url_el in root.findall("sm:url", _NS):
        loc_el = url_el.find("sm:loc", _NS)
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip()
        # Articles only — skip /category/, /videos, /contact, etc.
        if "/articles/" not in loc:
            continue

        lastmod_el = url_el.find("sm:lastmod", _NS)
        lastmod: Optional[datetime] = None
        if lastmod_el is not None and lastmod_el.text:
            try:
                # Format: 2026-06-07T19:10:17.601Z
                ts = lastmod_el.text.strip().replace("Z", "+00:00")
                lastmod = datetime.fromisoformat(ts)
            except Exception:
                pass

        out.append({"loc": loc, "lastmod": lastmod})

    # Sort newest first
    out.sort(
        key=lambda x: x["lastmod"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return out


# ============================================================
#  Article page parsing — extract title + published_time
# ============================================================

_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)
_PUBLISHED_RE = re.compile(
    r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _parse_article_meta(url: str) -> Dict[str, Any]:
    """Fetch an article HTML and extract title + published_time."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "InsightBridge-Brief/1.0"})
        if r.status_code != 200:
            return {"loc": url, "ok": False, "status": r.status_code}
        html = r.text

        og = _OG_TITLE_RE.search(html)
        title = og.group(1).strip() if og else None
        if not title:
            t = _TITLE_RE.search(html)
            if t:
                # strip " | Site Name" suffix if present
                title = re.split(r"\s*\|\s*", t.group(1))[0].strip()

        published: Optional[str] = None
        p = _PUBLISHED_RE.search(html)
        if p:
            published = p.group(1).strip()

        return {
            "loc": url,
            "ok": True,
            "title": title or "(untitled)",
            "published": published,
        }
    except Exception as e:
        logger.warning("Failed to parse article %s: %s", url, e)
        return {"loc": url, "ok": False, "error": str(e)}


# ============================================================
#  Public API — refresh headlines (run on schedule + on demand)
# ============================================================

async def refresh_sister_headlines(db) -> Dict[str, Any]:
    """
    Fetch newest sister articles, parse meta, store snapshot in MongoDB.
    Returns the refreshed records.
    """
    loop = asyncio.get_event_loop()

    def _do_fetch() -> List[Dict[str, Any]]:
        try:
            entries = _fetch_sister_sitemap_articles()
        except Exception:
            logger.exception("Sister sitemap fetch failed")
            return []
        # Take the newest N for the brief
        newest = entries[: max(ARTICLES_FOR_BRIEF, ARTICLES_FOR_SEO_PUSH)]
        results: List[Dict[str, Any]] = []
        for entry in newest:
            meta = _parse_article_meta(entry["loc"])
            if entry["lastmod"]:
                meta["lastmod"] = entry["lastmod"].isoformat()
            results.append(meta)
        return results

    records = await loop.run_in_executor(None, _do_fetch)
    if not records:
        return {"ok": False, "count": 0}

    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": SISTER_SITEMAP,
        "count": len(records),
        "items": records,
    }

    if db is not None:
        try:
            # keep one rolling snapshot doc + history
            await db.sister_headlines_snapshot.replace_one(
                {"_id": "latest"}, {**snapshot, "_id": "latest"}, upsert=True
            )
            await db.sister_headlines_history.insert_one(dict(snapshot))
        except Exception:
            logger.exception("Failed to persist sister headlines snapshot")

    logger.info("Sister headlines refreshed: %d items", len(records))
    return snapshot


async def get_brief_for_main_site(db, limit: int = ARTICLES_FOR_BRIEF) -> List[Dict[str, Any]]:
    """Return the latest N headlines for the main-site hero brief sidebar."""
    snap = None
    if db is not None:
        snap = await db.sister_headlines_snapshot.find_one(
            {"_id": "latest"}, {"_id": 0}
        )
    if not snap:
        # First-time call, fetch synchronously
        snap = await refresh_sister_headlines(db)
    items = (snap.get("items") or []) if snap else []
    # Keep only valid entries with titles
    items = [i for i in items if i.get("ok") and i.get("title")]
    return items[:limit]


async def get_urls_for_seo_push(db) -> List[str]:
    """Return newest sister article URLs to include in SEO push."""
    items = await get_brief_for_main_site(db, limit=ARTICLES_FOR_SEO_PUSH)
    return [i["loc"] for i in items]
