"""
Press citation stats fetcher — scrapes the sister site's /press page
(server-rendered) and extracts the "Cited & Syndicated Worldwide" counters
(citations / countries / languages) so the main site's trust strip stays in
sync automatically. Refreshes weekly via APScheduler.
"""
from __future__ import annotations

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

PRESS_URL = "https://intelligence.insightbridge.global/press"
REFRESH_INTERVAL_HOURS = 168  # weekly

_executor = ThreadPoolExecutor(max_workers=1)

_FALLBACK = {"citations": 9, "countries": 5, "languages": 3}


def _fetch_and_parse() -> Optional[Dict[str, int]]:
    resp = requests.get(PRESS_URL, timeout=20, headers={"User-Agent": "InsightBridge-MainSite/1.0"})
    resp.raise_for_status()
    html = resp.text.replace("<!-- -->", "")
    m = re.search(r'data-testid="press-citations-stats".*?</div>', html, re.S)
    block = m.group(0) if m else html
    stats = {}
    for key, pattern in (
        ("citations", r"(\d+)\s*citations?"),
        ("countries", r"(\d+)\s*countries"),
        ("languages", r"(\d+)\s*languages"),
    ):
        found = re.search(pattern, block, re.I)
        if not found:
            return None
        stats[key] = int(found.group(1))
    stats["platforms"] = len(set(re.findall(r'data-testid="press-citation-(\d+)"', html)))
    return stats


async def refresh_press_stats(db) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    try:
        stats = await loop.run_in_executor(_executor, _fetch_and_parse)
    except Exception:
        logger.exception("Press stats fetch failed")
        stats = None
    if not stats:
        return {"ok": False}
    snapshot = {
        "_id": "latest",
        **stats,
        "source": PRESS_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.press_stats_snapshot.replace_one({"_id": "latest"}, snapshot, upsert=True)
    logger.info("Press stats refreshed: %s", stats)
    return {"ok": True, **stats}


async def get_press_stats(db) -> Dict[str, Any]:
    snap = await db.press_stats_snapshot.find_one({"_id": "latest"})
    if snap:
        snap.pop("_id", None)
        return snap
    return {**_FALLBACK, "fallback": True}
