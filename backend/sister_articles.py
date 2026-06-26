"""
Sister-site article fetcher — pulls latest articles from
intelligence.insightbridge.global and exposes them for:
  1. /api/headlines    → main-site hero brief sidebar
  2. seo_push.py       → automatic submission to search engines

Primary source: the sister site's RSS feed at
  https://intelligence.insightbridge.global/api/rss.xml?lang=en
which is already ordered by article publish date (pubDate). This avoids the
problem of the XML sitemap, where a bulk republish can give many older
articles a near-identical <lastmod> and bury genuinely-new articles further
down the list.

Fallback: parse the sitemap + per-article HTML meta (slower, only used if
the RSS feed is unreachable).

Refreshes every 6 hours via APScheduler.
"""
from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

SISTER_DOMAIN = "intelligence.insightbridge.global"
SISTER_BASE = f"https://{SISTER_DOMAIN}"
SISTER_RSS = f"{SISTER_BASE}/api/rss.xml?lang=en"
SISTER_SITEMAP = f"{SISTER_BASE}/sitemap.xml"

REFRESH_INTERVAL_HOURS = 6
ARTICLES_FOR_BRIEF = 7        # how many to show on main site hero
ARTICLES_FOR_SEO_PUSH = 4     # newest 4 included in SEO push (keeps Baidu 10/day quota)


# ============================================================
#  Primary source: RSS feed
# ============================================================

_DC_NS = "{http://purl.org/dc/elements/1.1/}"


def _parse_rss_date(node: ET.Element) -> Optional[datetime]:
    """Prefer <dc:date> (ISO-8601 with µs) over <pubDate> (RFC-822)."""
    dc = node.find(f"{_DC_NS}date")
    if dc is not None and dc.text:
        try:
            return datetime.fromisoformat(dc.text.strip().replace("Z", "+00:00"))
        except Exception:
            pass
    pub = node.find("pubDate")
    if pub is not None and pub.text:
        try:
            dt = parsedate_to_datetime(pub.text.strip())
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
    return None


def _fetch_rss_articles(limit: int) -> List[Dict[str, Any]]:
    """Return the newest `limit` articles from the RSS feed, ordered newest-first."""
    resp = requests.get(SISTER_RSS, timeout=20, headers={"User-Agent": "InsightBridge-Brief/1.0"})
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    items: List[Dict[str, Any]] = []
    for item in root.iter("item"):
        link_el = item.find("link")
        title_el = item.find("title")
        if link_el is None or not link_el.text:
            continue
        loc = link_el.text.strip()
        if "/articles/" not in loc:
            continue
        title = (title_el.text or "").strip() if title_el is not None else ""
        pub_dt = _parse_rss_date(item)
        items.append({
            "loc": loc,
            "ok": True,
            "title": title or "(untitled)",
            "published": pub_dt.isoformat() if pub_dt else None,
            "_sort_dt": pub_dt or datetime.min.replace(tzinfo=timezone.utc),
        })

    items.sort(key=lambda x: x["_sort_dt"], reverse=True)
    for it in items:
        it.pop("_sort_dt", None)
    return items[:limit]


# ============================================================
#  Fallback source: sitemap + per-article HTML meta parsing
# ============================================================

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)
_PUBLISHED_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _fetch_sister_sitemap_articles() -> List[Dict[str, Any]]:
    resp = requests.get(SISTER_SITEMAP, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    out: List[Dict[str, Any]] = []
    for url_el in root.findall("sm:url", _NS):
        loc_el = url_el.find("sm:loc", _NS)
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip()
        if "/articles/" not in loc:
            continue

        lastmod_el = url_el.find("sm:lastmod", _NS)
        lastmod: Optional[datetime] = None
        if lastmod_el is not None and lastmod_el.text:
            try:
                ts = lastmod_el.text.strip().replace("Z", "+00:00")
                lastmod = datetime.fromisoformat(ts)
            except Exception:
                pass
        out.append({"loc": loc, "lastmod": lastmod})

    out.sort(
        key=lambda x: x["lastmod"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return out


def _parse_article_meta(url: str) -> Dict[str, Any]:
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


def _fallback_via_sitemap(limit: int) -> List[Dict[str, Any]]:
    """Only used if the RSS feed is unreachable. Parses every article in the
    sitemap concurrently and re-sorts by article:published_time."""
    entries = _fetch_sister_sitemap_articles()
    if not entries:
        return []
    with ThreadPoolExecutor(max_workers=10) as pool:
        parsed = list(pool.map(lambda e: (e, _parse_article_meta(e["loc"])), entries))

    results: List[Dict[str, Any]] = []
    for entry, meta in parsed:
        if not meta.get("ok"):
            continue
        sort_dt: Optional[datetime] = None
        pub = meta.get("published")
        if pub:
            try:
                sort_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except Exception:
                sort_dt = None
        if sort_dt is None and entry["lastmod"]:
            sort_dt = entry["lastmod"]
        meta["_sort_dt"] = sort_dt or datetime.min.replace(tzinfo=timezone.utc)
        if entry["lastmod"]:
            meta["lastmod"] = entry["lastmod"].isoformat()
        results.append(meta)

    results.sort(key=lambda x: x["_sort_dt"], reverse=True)
    for r in results:
        r.pop("_sort_dt", None)
    return results[:limit]


# ============================================================
#  Public API
# ============================================================

async def refresh_sister_headlines(db) -> Dict[str, Any]:
    """Fetch newest sister articles, store snapshot in MongoDB, return it."""
    loop = asyncio.get_event_loop()
    limit = max(ARTICLES_FOR_BRIEF, ARTICLES_FOR_SEO_PUSH)

    def _do_fetch() -> List[Dict[str, Any]]:
        try:
            items = _fetch_rss_articles(limit)
            if items:
                logger.info("Sister headlines: fetched %d from RSS", len(items))
                return items
            logger.warning("RSS feed returned empty; falling back to sitemap")
        except Exception:
            logger.exception("RSS feed fetch failed; falling back to sitemap")
        try:
            return _fallback_via_sitemap(limit)
        except Exception:
            logger.exception("Sitemap fallback also failed")
            return []

    records = await loop.run_in_executor(None, _do_fetch)
    if not records:
        return {"ok": False, "count": 0}

    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": SISTER_RSS,
        "count": len(records),
        "items": records,
    }

    if db is not None:
        try:
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
        snap = await refresh_sister_headlines(db)
    items = (snap.get("items") or []) if snap else []
    items = [i for i in items if i.get("ok") and i.get("title")]
    return items[:limit]


async def get_urls_for_seo_push(db) -> List[str]:
    """Return newest sister article URLs to include in SEO push."""
    items = await get_brief_for_main_site(db, limit=ARTICLES_FOR_SEO_PUSH)
    return [i["loc"] for i in items]
