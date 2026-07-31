"""
Press citation stats + list fetcher — scrapes the sister site's /press page
(server-rendered) and extracts:
  1) the "Cited & Syndicated Worldwide" counters (citations / countries / languages)
  2) the full ordered list of citation cards (flag, platform name, category label,
     source URL) so the main site's trust strip stays in sync automatically without
     hand-editing HTML each time a new citation lands.
Refreshes weekly via APScheduler.
"""
from __future__ import annotations

import asyncio
import html as _html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

PRESS_URL = "https://intelligence.insightbridge.global/press"
REFRESH_INTERVAL_HOURS = 168  # weekly

_executor = ThreadPoolExecutor(max_workers=1)

# Static fallback used when the sister site is unreachable AND the db has no
# cached snapshot yet. Values stay conservative — the live scraper immediately
# overwrites them on first successful fetch.
_FALLBACK_STATS = {"citations": 11, "countries": 6, "languages": 3, "platforms": 11}
_FALLBACK_LIST: List[Dict[str, str]] = [
    {"flag": "🇺🇸", "platform": "Event Planner News", "note": "Robotics White Paper Feature", "url": "https://eventplannernews.com/211947/2027-global-hotel-industry-white-paperthe-robotics-revolution-and-asset-binary-divergence"},
    {"flag": "🇷🇺", "platform": "Hotel.Report", "note": "Russia / CIS Full Republication", "url": "https://hotel.report/development/the-ultra-luxury-hotel-margin-illusion-how-asset-light-giants-are-transferring-heavy-asset-risk-to-owners"},
    {"flag": "🇺🇸", "platform": "Muck Rack", "note": "Verified Journalist Profile", "url": "https://muckrack.com/tong-yin/articles"},
    {"flag": "🇨🇳", "platform": "TTG China", "note": "Feature Interview", "url": "https://ttgchina.com/2026/07/08/"},
    {"flag": "🇯🇵", "platform": "HotelX Tech", "note": 'Coined "AI シアター" term', "url": "https://hotelx.tech/"},
    {"flag": "🇨🇱", "platform": "Canadian Reviews", "note": "Full-Text Republication", "url": "https://noticiasenvivo.cl/ai-will-not-transform-hotels-until-it-changes-the-meeting/"},
    {"flag": "🌐", "platform": "AI Hospitality Alliance", "note": "2× Insights Features", "url": "https://aihospitalityalliance.com/insights/why-ai-pricing-fails-hotels"},
    {"flag": "🌐", "platform": "AI for Tourism & Hospitality", "note": "Feature Article", "url": "https://aitourismandhospitality.com/story/ai-pricing-fails-hotels-2026"},
    {"flag": "🌐", "platform": "Let's Data Science", "note": "Editorial Summary", "url": "https://letsdatascience.com/news/ai-helps-hotels-only-if-managers-improve-decision-making-d6a266f6"},
]

# Curated pretty descriptions per platform — override the raw "Localized Syndication"
# style category labels that the sister-site DOM exposes. Keyed by a substring of the
# platform name (case-insensitive). Any new sister-site platform without an override
# falls back to the raw category, so new citations appear automatically — you just
# lose the marketing polish until the next content update here.
_NOTE_OVERRIDES: Dict[str, str] = {
    "event planner": "Robotics White Paper Feature",
    "hotel.report": "Russia / CIS Full Republication",
    "muck rack": "Verified Journalist Profile",
    "ttg china": "Feature Interview",
    "hotelx": 'Coined "AI シアター" term',
    "canadian reviews": "Full-Text Republication",
    "ai hospitality alliance": "2× Insights Features",
    "ai for tourism": "Feature Article",
    "let's data science": "Editorial Summary",
}

# Regex to pull one full citation card. Each card starts with a <a href="URL" ...
# data-testid="press-citation-N"...> and ends at the closing </a>.
_CARD_RE = re.compile(
    r'<a[^>]*?href="(?P<url>[^"]+)"[^>]*?data-testid="press-citation-(?P<idx>\d+)"[^>]*?>(?P<inner>.*?)</a>',
    re.S,
)
_FLAG_RE = re.compile(r'aria-label="country"[^>]*>([^<]+)</span>')
_PLATFORM_RE = re.compile(
    r'text-burgundy\s+bg-burgundy[^>]*>([^<]+)</span>'
)
_CATEGORY_RE = re.compile(
    r'text-ink/55"[^>]*>([^<]+)</span>'
)
_STRIP_TAGS = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return _html.unescape(_STRIP_TAGS.sub("", text)).strip()


def _fetch_and_parse() -> Optional[Dict[str, Any]]:
    resp = requests.get(PRESS_URL, timeout=25, headers={"User-Agent": "InsightBridge-MainSite/1.0"})
    resp.raise_for_status()
    html = resp.text.replace("<!-- -->", "")

    # 1) counters
    m = re.search(r'data-testid="press-citations-stats".*?</div>', html, re.S)
    block = m.group(0) if m else html
    stats: Dict[str, int] = {}
    for key, pattern in (
        ("citations", r"(\d+)\s*citations?"),
        ("countries", r"(\d+)\s*countries"),
        ("languages", r"(\d+)\s*languages"),
    ):
        found = re.search(pattern, block, re.I)
        if not found:
            return None
        stats[key] = int(found.group(1))

    # 2) full list of citation cards
    items: List[Dict[str, str]] = []
    for match in _CARD_RE.finditer(html):
        idx = int(match.group("idx"))
        url = _html.unescape(match.group("url"))
        inner = match.group("inner")
        flag_m = _FLAG_RE.search(inner)
        platform_m = _PLATFORM_RE.search(inner)
        cat_m = _CATEGORY_RE.search(inner)
        if not (flag_m and platform_m):
            continue
        flag = _clean(flag_m.group(1))
        # Some entries flag "Global" with the 🌐 emoji already; keep as-is.
        # Occasional entries use non-country emojis like ✦ — force 🌐 for those.
        if not flag or len(flag) > 4:
            flag = "🌐"
        items.append({
            "idx": idx,
            "flag": flag,
            "platform": _clean(platform_m.group(1)),
            "note": _clean(cat_m.group(1)) if cat_m else "",
            "url": url,
        })
    items.sort(key=lambda x: x["idx"])
    for it in items:
        it.pop("idx", None)

    # 3) collapse duplicate (platform, note) pairs — e.g. HotelX Tech twice — into
    #    one row with a "N×" suffix on the note, preserving the newest URL first
    #    (which is `items[0]` since sister site is reverse-chronological).
    seen: Dict[str, Dict[str, str]] = {}
    ordered: List[Dict[str, str]] = []
    for it in items:
        key = it["platform"]
        if key in seen:
            seen[key]["count"] = seen[key].get("count", 1) + 1
        else:
            it["count"] = 1
            seen[key] = it
            ordered.append(it)
    for it in ordered:
        if it["count"] > 1:
            it["note"] = f'{it["count"]}× {it["note"]}' if it["note"] else f'{it["count"]}× Features'
        it.pop("count", None)
        # Apply curated marketing note override where we have one
        platform_lower = it["platform"].lower()
        for key, pretty in _NOTE_OVERRIDES.items():
            if key in platform_lower:
                it["note"] = pretty
                break
        # Attach Wayback Machine archived snapshot (for the "📎 已存档" badge on
        # the trust strip). Silently no-op if Wayback is unreachable or the URL
        # was never archived — the badge simply doesn't render.
        try:
            from wayback import check_availability
            wayback = check_availability(it["url"])
            if wayback:
                it["wayback_url"] = wayback["archived_url"]
                it["wayback_ts"]  = wayback["timestamp"]
        except Exception:
            logger.exception("Wayback enrichment skipped for %s", it["url"])

    stats["platforms"] = len(ordered)
    return {**stats, "list": ordered}


async def refresh_press_stats(db) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    try:
        parsed = await loop.run_in_executor(_executor, _fetch_and_parse)
    except Exception:
        logger.exception("Press stats fetch failed")
        parsed = None
    if not parsed:
        return {"ok": False}
    citation_list = parsed.pop("list", [])
    snapshot = {
        "_id": "latest",
        **parsed,
        "list": citation_list,
        "source": PRESS_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.press_stats_snapshot.replace_one({"_id": "latest"}, snapshot, upsert=True)
    logger.info("Press stats refreshed: %s (list=%d)", {k: v for k, v in parsed.items()}, len(citation_list))
    return {"ok": True, **parsed, "list_count": len(citation_list)}


async def get_press_stats(db) -> Dict[str, Any]:
    """Counter-only endpoint — kept for backwards-compat with existing frontend."""
    snap = await db.press_stats_snapshot.find_one({"_id": "latest"})
    if snap:
        snap.pop("_id", None)
        snap.pop("list", None)  # counters only for this endpoint
        return snap
    return {**_FALLBACK_STATS, "fallback": True}


async def get_press_citations(db) -> Dict[str, Any]:
    """Full citation payload — counters + ordered platform list — for the
    dynamic 'Cited & Syndicated Worldwide' trust strip on the main site."""
    snap = await db.press_stats_snapshot.find_one({"_id": "latest"})
    if snap and snap.get("list"):
        snap.pop("_id", None)
        _ensure_hnr_scorecard(snap)
        return snap
    fallback = {**_FALLBACK_STATS, "list": list(_FALLBACK_LIST), "fallback": True}
    _ensure_hnr_scorecard(fallback)
    return fallback


# ------------------------------------------------------------------
# HNR Vision 2030 Scorecard — always present at position #0
# ------------------------------------------------------------------
_HNR_SCORECARD_ROW = {
    "flag": "🇺🇸",
    "platform": "Hotel News Resource",
    "note": "Vision 2030 Scorecard — first-run Jul 29, 2026 · article 142297",
    "url": "https://www.hotelnewsresource.com/article142297.html",
}


def _ensure_hnr_scorecard(payload: Dict[str, Any]) -> None:
    """Guarantee the HNR Scorecard citation is always the first row of the
    'Cited & Syndicated Worldwide' strip. Sister-site scrape can lag behind
    a same-day cross-publication (as happened on Jul 29, 2026), so this is
    the durable server-side fallback."""
    lst = payload.get("list")
    if not isinstance(lst, list):
        return
    has_hnr = any(
        "hotelnewsresource.com/article142297" in (it.get("url") or "")
        for it in lst
    )
    if not has_hnr:
        lst.insert(0, dict(_HNR_SCORECARD_ROW))
        payload["list"] = lst
