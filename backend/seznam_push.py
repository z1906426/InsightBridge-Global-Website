"""
Seznam Webmaster reindex-push module.

Seznam.cz (Czech search engine, ~20% of Czech search market) is already a
member of the IndexNow protocol so our IndexNow submissions reach it. This
module adds a **direct** reindex request via Seznam's Webmaster API for two
reasons:

  1. Confirmation — the reindex endpoint returns a JSON response describing
     whether the URL was accepted, which we log to Mongo. IndexNow only
     returns a global 200/202.
  2. Redundancy — if IndexNow ever de-registers our key or has an outage,
     the direct API keeps working.

Endpoint (verified 2026-07-12 via probe):
    POST https://reporter.seznam.cz/wm-api/web/document/reindex
        ?key=<API_KEY>&url=<URL_ENCODED_URL>
    (no Authorization header required — the key is authenticated via the
     `key` query parameter; older docs mentioning `Authorization: key ...`
     header are outdated and return 400 "Missing query parameter 'key'")

The key is obtained from https://reporter.seznam.cz/wm/ after site
verification. Stored in `SEZNAM_API_KEY` env var.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

SEZNAM_API_KEY = os.environ.get("SEZNAM_API_KEY", "")
SEZNAM_ENDPOINT = "https://reporter.seznam.cz/wm-api/web/document/reindex"

# Per-request cap — daily quota is not officially documented; we mirror the
# Baidu safety cap (10/day) to stay well within polite-crawler limits.
DEFAULT_MAX_URLS = 10


def push_to_seznam(urls: List[str], *, max_urls: int = DEFAULT_MAX_URLS) -> Dict[str, Any]:
    """Submit up to `max_urls` URLs to Seznam's Webmaster reindex API.

    Returns a summary dict with per-URL statuses so we can see exactly
    which URLs Seznam accepted.
    """
    if not SEZNAM_API_KEY:
        return {"engine": "seznam", "ok": False, "error": "SEZNAM_API_KEY not set"}
    if not urls:
        return {"engine": "seznam", "ok": False, "error": "no urls provided"}

    capped = urls[:max_urls]
    per_url: List[Dict[str, Any]] = []
    ok_count = 0

    for u in capped:
        params = {"key": SEZNAM_API_KEY, "url": u}
        try:
            r = requests.post(
                SEZNAM_ENDPOINT,
                params=params,
                timeout=15,
            )
            try:
                body: Any = r.json()
            except Exception:
                body = r.text[:200]
            # Seznam returns 200 on accepted reindex.
            is_ok = r.status_code == 200
            if is_ok:
                ok_count += 1
            per_url.append(
                {
                    "url": u,
                    "status_code": r.status_code,
                    "response": body,
                    "ok": is_ok,
                }
            )
        except Exception as e:
            logger.exception("Seznam reindex failed for %s", u)
            per_url.append({"url": u, "ok": False, "error": str(e)})

    return {
        "engine": "seznam",
        "ok": ok_count > 0,
        "urls_submitted": len(capped),
        "urls_accepted": ok_count,
        "urls_capped": len(urls) - len(capped) if len(urls) > max_urls else 0,
        "per_url": per_url,
    }
