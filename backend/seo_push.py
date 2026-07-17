"""
SEO push module — submits site URLs to search engines on a schedule.

Engines covered:
  - Baidu Zhanzhang API (data.zz.baidu.com)  — Chinese search
  - IndexNow API (api.indexnow.org)          — Bing, Yandex, Seznam, Naver, Yep

Triggered by:
  - APScheduler interval job (every 24 h) configured in seo_scheduler.py
  - Manual API endpoint:  POST /api/seo/push
  - Publications push:    POST /api/seo/push-publications
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

# ─── Baidu daily-quota smart selection ────────────────────────────────────
# The Baidu Zhanzhang push API allows ~10 URLs/day for standard sites. Rather
# than pushing the same 8 fixed URLs every day (and eating quota with no fresh
# information for the crawler), we:
#   1. ALWAYS push a small must-push set (per user directive 2026-07-17)
#   2. Rotate through the remainder on a 3-day cooldown per URL
#   3. Cap total at 9 (leaves 1 quota slot as buffer)
#
# The MUST_PUSH_URLS list is applied to EVERY engine (Baidu, IndexNow, Google,
# Seznam) — per user directive 2026-07-17 (later that night): these three
# SPA sections must be re-crawled on every daily push. Baidu accepts the
# `#fragment` URLs literally; Google typically treats them as the base
# `/index.html` and increments its "please re-crawl" signal accordingly.
MUST_PUSH_URLS: List[str] = [
    f"{SITE_URL}/index.html#news",
    f"{SITE_URL}/index.html#about",
    f"{SITE_URL}/index.html#services",
]
# Alias kept for backwards-compat / tests
BAIDU_MUST_PUSH = MUST_PUSH_URLS
BAIDU_URL_COOLDOWN_DAYS = 3
BAIDU_PUSH_CAP = 9  # leave 1 slot buffer under the 10/day quota


def _prepend_must_push(urls: List[str]) -> List[str]:
    """Return [must-push URLs first, then the caller's list], de-duplicated.
    Used to guarantee every engine's payload includes MUST_PUSH_URLS while
    respecting the caller's own priority ordering for everything after."""
    seen: set[str] = set()
    out: List[str] = []
    for u in list(MUST_PUSH_URLS) + list(urls):
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


async def _select_baidu_urls(db, candidate_urls: List[str]) -> List[str]:
    """Pick which URLs to submit to Baidu on this push.

    Rule:
      - Every push includes the 3 must-push URLs (news / about / services SPA
        hashes on the homepage) — user directive.
      - Fill remaining slots (up to BAIDU_PUSH_CAP total) with `candidate_urls`,
        skipping any URL that Baidu already accepted in the last N days.
      - Order in the payload preserves priority (must-push first, then whatever
        `get_urls()` ordered by importance).
    """
    from datetime import datetime, timedelta, timezone as tz

    selected: List[str] = list(BAIDU_MUST_PUSH)
    seen = set(selected)

    if db is None:
        # No cooldown tracking possible → just fill by priority up to cap
        for u in candidate_urls:
            if len(selected) >= BAIDU_PUSH_CAP:
                break
            if u not in seen:
                selected.append(u)
                seen.add(u)
        return selected

    # Look up which URLs were pushed to Baidu within the cooldown window
    cutoff = (datetime.now(tz.utc) - timedelta(days=BAIDU_URL_COOLDOWN_DAYS)).isoformat()
    recent_docs = db.baidu_url_lastpush.find(
        {"pushed_at": {"$gte": cutoff}},
        projection={"_id": 0, "url": 1},
    )
    recently_pushed = {doc["url"] async for doc in recent_docs}

    # Fill remaining slots
    for u in candidate_urls:
        if len(selected) >= BAIDU_PUSH_CAP:
            break
        if u in seen:
            continue
        if u in recently_pushed:
            logger.debug("Baidu: skipping %s (pushed within %sd cooldown)", u, BAIDU_URL_COOLDOWN_DAYS)
            continue
        selected.append(u)
        seen.add(u)

    # If everything in `candidate_urls` is in cooldown, respect it — just push
    # the must-push list this round. Saves quota; those URLs will come out of
    # cooldown after 3 days and get pushed again then.
    return selected


async def _record_baidu_push(db, urls: List[str], success: bool) -> None:
    """Save timestamps of URLs successfully accepted by Baidu so cooldown works."""
    if db is None or not success or not urls:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        for u in urls:
            await db.baidu_url_lastpush.update_one(
                {"url": u},
                {"$set": {"url": u, "pushed_at": now}},
                upsert=True,
            )
    except Exception:
        logger.exception("Failed to record Baidu URL lastpush timestamps")


def get_urls() -> List[str]:
    """Return the canonical list of URLs to submit, in **priority order**.

    Per operator directive (2026-07-13):
      1st  — homepage `/`                                       (must-push every day)
      2nd  — RSS feed `/rss.xml`                                (must-push every day)
      3rd  — Executive-bio standalone page `/about.html`        (must-push every day)
      then — other own-site canonical pages in decreasing importance.

    URLs republished from external platforms (Skift, PhocusWire, Hospitality Net,
    Hotel News Resource — i.e. the `/media/IB_*.pdf` files) are intentionally
    EXCLUDED from this list. Those outlets syndicate the originals themselves;
    duplicating our republished copies would be redundant and could dilute the
    canonical signal.
    """
    pages = [
        # === Priority 1-3: must-push every day ===
        "/",                                     # homepage
        "/rss.xml",                              # RSS feed — crawlers subscribe
        "/about.html",                           # executive-bio standalone page
        # === Other own-site canonical pages ===
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


async def run_push_urls(db, urls: List[str], *, label: str = "custom") -> Dict[str, Any]:
    """Push an explicit list of URLs (e.g. publications) to all engines and log.

    Baidu has a strict 10 URLs/day quota → smart selection (see _select_baidu_urls).
    IndexNow accepts up to 10,000/payload so we pass them all.
    """
    if not urls:
        return {"ok_all": False, "error": "no urls provided"}

    # De-dup while preserving order
    seen: set[str] = set()
    deduped: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        deduped.append(u)

    same_host_urls = [u for u in deduped if SITE_DOMAIN in u]
    baidu_urls = await _select_baidu_urls(db, same_host_urls)
    # Every engine gets the must-push URLs prepended (per user directive 2026-07-17)
    indexnow_urls = _prepend_must_push(deduped)                # IndexNow: generous quota, includes cross-host URLs
    google_urls = _prepend_must_push(same_host_urls[:47])      # Google: cap 50; leave room for 3 must-push
    seznam_urls = _prepend_must_push(same_host_urls)           # Seznam: prepend then let its own capper handle

    logger.info(
        "SEO push [%s]: Baidu=%d (capped@10), IndexNow=%d, Google=%d",
        label, len(baidu_urls), len(indexnow_urls), len(google_urls),
    )

    from google_indexing import push_to_google  # lazy import
    from seznam_push import push_to_seznam       # lazy import

    results = [
        push_to_baidu(baidu_urls) if baidu_urls else {"engine": "baidu", "ok": False, "skipped": "no same-host urls"},
        push_to_indexnow(indexnow_urls),
        push_to_google(google_urls),
        push_to_seznam(seznam_urls),              # Seznam Webmaster reindex API (Czech search)
    ]
    # Track per-URL Baidu push timestamps so the 3-day cooldown works next round
    await _record_baidu_push(db, baidu_urls, results[0].get("ok", False))

    record: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "urls_count": len(indexnow_urls),
        "urls": indexnow_urls,
        "baidu_urls_count": len(baidu_urls),
        "results": results,
        "ok_all": all(r.get("ok") for r in results),
    }
    try:
        if db is not None:
            await db.seo_pushes.insert_one(dict(record))
    except Exception:
        logger.exception("Failed to persist seo push record (%s)", label)

    return record


async def run_push_and_save(db) -> Dict[str, Any]:
    """Run pushes to all engines, log to MongoDB, return summary."""
    main_urls = get_urls()

    # Augment with the 4 newest sister-site article URLs (IndexNow only;
    # Baidu rejects them as "not_same_site" since the sister site has its
    # own Baidu Zhanzhang registration).
    try:
        from sister_articles import get_urls_for_seo_push
        sister_urls = await get_urls_for_seo_push(db)
    except Exception:
        logger.exception("Could not load sister-site URLs for SEO push")
        sister_urls = []

    indexnow_urls = _prepend_must_push(main_urls + sister_urls)   # IndexNow accepts both hosts
    baidu_urls = await _select_baidu_urls(db, main_urls)          # Baidu: smart-selected, own must-push handling
    google_urls = _prepend_must_push(main_urls)                   # Google: same-domain only

    logger.info(
        "SEO push: Baidu=%d (smart-selected under 10/day quota); IndexNow=%d (apex+sister); Google=%d",
        len(baidu_urls), len(indexnow_urls), len(google_urls),
    )

    from google_indexing import push_to_google  # lazy import
    from seznam_push import push_to_seznam       # lazy import

    results = [
        push_to_baidu(baidu_urls),
        push_to_indexnow(indexnow_urls),
        push_to_google(google_urls),
        push_to_seznam(_prepend_must_push(main_urls)),   # Seznam Webmaster reindex API (Czech search)
    ]
    # Track per-URL Baidu push timestamps so the 3-day cooldown works next round
    await _record_baidu_push(db, baidu_urls, results[0].get("ok", False))

    record: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "urls_count": len(indexnow_urls),
        "urls": indexnow_urls,
        "main_urls_count": len(main_urls),
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
        "SEO push: done. baidu_ok=%s, indexnow_ok=%s, google_ok=%s, seznam_ok=%s",
        results[0].get("ok"),
        results[1].get("ok"),
        results[2].get("ok"),
        results[3].get("ok"),
    )
    return record
