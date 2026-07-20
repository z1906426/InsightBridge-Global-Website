"""
wayback.py — Internet Archive Wayback Machine integration.

Two features:
  1. check_availability(url)   → look up the closest existing snapshot
                                  (used by press_stats to attach a "📎 archived"
                                  badge to every citation on the trust strip).
  2. save_page_now(url)         → actively request Wayback to snapshot our own
                                  important pages so we have a permanent,
                                  third-party-verified timestamped record.

Both endpoints are public / no-auth. Wayback rate-limits Save Page Now to
~10 req/min for anonymous callers; we run it weekly for a handful of URLs so
we stay well under that.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

AVAILABILITY_ENDPOINT = "https://archive.org/wayback/available"
SAVE_ENDPOINT = "https://web.archive.org/save/"
# Note: Wayback's "Save Page Now" endpoint returns 429 to identifiable bot
# User-Agents (e.g. "InsightBridge-MainSite/1.0"). A browser-shaped UA gets
# through the anonymous rate-limit filter fine. See 2026-07-20 debug notes.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def check_availability(url: str, timeout: int = 12) -> Optional[Dict[str, str]]:
    """Return `{archived_url, timestamp}` for the closest existing snapshot,
    or None if the URL has never been archived / API is unreachable."""
    try:
        r = requests.get(
            AVAILABILITY_ENDPOINT,
            params={"url": url},
            headers={"User-Agent": UA},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        logger.exception("Wayback availability check failed for %s", url)
        return None

    snap = (data.get("archived_snapshots") or {}).get("closest") or {}
    if not snap.get("available"):
        return None
    return {
        "archived_url": snap.get("url", ""),
        "timestamp":    snap.get("timestamp", ""),   # YYYYMMDDhhmmss
    }


def save_page_now(url: str, timeout: int = 45) -> Dict[str, Any]:
    """Actively request a fresh Wayback snapshot of `url`. Returns a dict
    with `{ok, url, archived_url, status_code}`. Wayback may respond 200
    OK long before the snapshot is fully written; the archived URL is
    returned in the `content-location` header."""
    try:
        r = requests.get(
            SAVE_ENDPOINT + url,
            headers={"User-Agent": UA},
            timeout=timeout,
            allow_redirects=True,
        )
        # Wayback puts the finished snapshot path in Content-Location on success.
        archived_path = r.headers.get("Content-Location") or ""
        archived_url = f"https://web.archive.org{archived_path}" if archived_path else ""
        return {
            "ok": r.status_code < 400,
            "url": url,
            "archived_url": archived_url,
            "status_code": r.status_code,
        }
    except Exception as e:
        logger.exception("Wayback save_page_now failed for %s", url)
        return {"ok": False, "url": url, "error": str(e)[:200]}


def save_pages_now(urls: List[str], pause_seconds: float = 6.5) -> List[Dict[str, Any]]:
    """Save a batch of URLs to Wayback, spacing requests to respect the
    ~10-req/min anonymous rate limit."""
    results: List[Dict[str, Any]] = []
    for i, u in enumerate(urls):
        if i > 0:
            time.sleep(pause_seconds)
        results.append(save_page_now(u))
    return results
