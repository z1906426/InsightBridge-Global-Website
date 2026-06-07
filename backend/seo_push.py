"""
SEO push module — submits site URLs to search engines on a schedule.

Engines covered:
  - Baidu Zhanzhang API (data.zz.baidu.com)  — Chinese search
  - IndexNow API (api.indexnow.org)          — Bing, Yandex, Seznam, Naver, Yep

Triggered by:
  - APScheduler interval job (every 72 h) configured in seo_scheduler.py
  - Manual API endpoint:  POST /api/seo/push
"""
from __future__ import annotations

import os
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "insightbridge.global")
SITE_URL = f"https://{SITE_DOMAIN}"

INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "")
BAIDU_PUSH_TOKEN = os.environ.get("BAIDU_PUSH_TOKEN", "")


def get_urls() -> List[str]:
    """Return the canonical list of URLs to submit (sitemap-aligned)."""
    pages = [
        "/",
        "/zh.html",
        "/tools.html",
        "/intelligence-market-report.html",
        "/intelligence-vol01.html",
        "/privacy.html",
    ]
    return [f"{SITE_URL}{p}" for p in pages]


def push_to_baidu(urls: List[str]) -> Dict[str, Any]:
    """POST URLs as newline-separated text to Baidu Zhanzhang API."""
    if not BAIDU_PUSH_TOKEN:
        return {"engine": "baidu", "ok": False, "error": "BAIDU_PUSH_TOKEN not set"}

    endpoint = (
        f"http://data.zz.baidu.com/urls"
        f"?site={SITE_URL}&token={BAIDU_PUSH_TOKEN}"
    )
    body = "\n".join(urls).encode("utf-8")
    try:
        r = requests.post(
            endpoint,
            data=body,
            headers={"Content-Type": "text/plain"},
            timeout=15,
        )
        try:
            payload = r.json()
        except Exception:
            payload = r.text[:500]
        return {
            "engine": "baidu",
            "ok": r.status_code == 200 and isinstance(payload, dict) and "success" in payload,
            "status_code": r.status_code,
            "response": payload,
            "urls_submitted": len(urls),
        }
    except Exception as e:
        logger.exception("Baidu push failed")
        return {"engine": "baidu", "ok": False, "error": str(e)}


def push_to_indexnow(urls: List[str]) -> Dict[str, Any]:
    """POST URL list to IndexNow — covers Bing, Yandex, Seznam, Naver, Yep."""
    if not INDEXNOW_KEY:
        return {"engine": "indexnow", "ok": False, "error": "INDEXNOW_KEY not set"}

    endpoint = "https://api.indexnow.org/IndexNow"
    payload = {
        "host": SITE_DOMAIN,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    try:
        r = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=20,
        )
        # IndexNow returns 200 (URLs accepted) or 202 (received, will be processed)
        ok = r.status_code in (200, 202)
        return {
            "engine": "indexnow",
            "ok": ok,
            "status_code": r.status_code,
            "response": r.text[:300] if r.text else "(empty body)",
            "urls_submitted": len(urls),
            "covers": ["Bing", "Yandex", "Naver", "Seznam", "Yep/DuckDuckGo"],
        }
    except Exception as e:
        logger.exception("IndexNow push failed")
        return {"engine": "indexnow", "ok": False, "error": str(e)}


async def run_push_and_save(db) -> Dict[str, Any]:
    """Run pushes to all engines, log to MongoDB, return summary."""
    urls = get_urls()

    # Augment with the 4 newest sister-site article URLs
    try:
        from sister_articles import get_urls_for_seo_push
        sister_urls = await get_urls_for_seo_push(db)
        urls = urls + sister_urls
    except Exception:
        logger.exception("Could not load sister-site URLs for SEO push")
        sister_urls = []

    logger.info(
        "SEO push: submitting %d URLs (%d main + %d sister) to Baidu + IndexNow",
        len(urls), len(urls) - len(sister_urls), len(sister_urls),
    )

    results = [
        push_to_baidu(urls),
        push_to_indexnow(urls),
    ]

    record: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "urls_count": len(urls),
        "urls": urls,
        "main_urls_count": len(urls) - len(sister_urls),
        "sister_urls_count": len(sister_urls),
        "results": results,
        "ok_all": all(r.get("ok") for r in results),
    }
    try:
        if db is not None:
            await db.seo_pushes.insert_one(dict(record))
    except Exception:
        logger.exception("Failed to persist seo push record")

    logger.info(
        "SEO push: done. baidu_ok=%s, indexnow_ok=%s",
        results[0].get("ok"),
        results[1].get("ok"),
    )
    return record
