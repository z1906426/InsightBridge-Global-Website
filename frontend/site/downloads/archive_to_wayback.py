#!/usr/bin/env python3
"""archive_to_wayback.py — submit InsightBridge Global URLs to the Internet
Archive Wayback Machine (Save Page Now).

Run this on your Mac terminal:

    cd ~/Downloads   # or wherever you saved this file
    python3 archive_to_wayback.py

Requirements: Python 3.7+ (standard library only — no pip install needed).
No API key required for basic public Save Page Now requests.

Behaviour:
  * Submits each URL to https://web.archive.org/save/<url>
  * Waits ~7 seconds between requests to respect Internet Archive rate limits
  * Follows redirects — a successful save returns HTTP 200 with a Location or
    Content-Location header pointing at the archived snapshot
  * Retries once on timeout / 5xx
  * Prints progress in real time
  * Writes a JSON report to ./archive_report.json for auditing

Total run time: ~46 URLs × ~50s per URL = ~40 minutes. Leave the terminal
open — Mac's App Nap won't affect it since it's a foreground process.
"""

from __future__ import annotations

import datetime as dt
import http.client
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------------------
# All 46 InsightBridge Global URLs to archive (auto-generated 2026-02-26).
# ---------------------------------------------------------------------------
URL_LIST = [
    "https://insightbridge.global/",
    "https://insightbridge.global/rss.xml",
    "https://insightbridge.global/about.html",
    "https://insightbridge.global/zh.html",
    "https://insightbridge.global/tools.html",
    "https://insightbridge.global/intelligence-market-report.html",
    "https://insightbridge.global/intelligence-vol01.html",
    "https://insightbridge.global/privacy.html",
    "https://insightbridge.global/publications/",
    "https://insightbridge.global/sitemap.xml",
    "https://insightbridge.global/theories/core-code-theory.html",
    "https://insightbridge.global/theories/ddrt.html",
    "https://insightbridge.global/theories/home-model.html",
    "https://insightbridge.global/theories/management-debt.html",
    "https://insightbridge.global/landing/ai-pricing.html",
    "https://insightbridge.global/publications/xian-incident-republican-china-politics.html",
    "https://insightbridge.global/publications/antecedents-consumer-reference-price-2007.html",
    "https://insightbridge.global/publications/cong-zha-qu-wen-ming-dao-jia-yuan-wen-ming-zhi-ku-zhuan-gao-xiu-ding-ban.html",
    "https://insightbridge.global/publications/core-code-theory-amr.html",
    "https://insightbridge.global/publications/ddrt-strategic-organization-v3.html",
    "https://insightbridge.global/publications/dpr-plc-neural-financial-model.html",
    "https://insightbridge.global/publications/from-extraction-to-home-civilization-think-tank-report.html",
    "https://insightbridge.global/publications/hbs-case-study-chinese.html",
    "https://insightbridge.global/publications/hbs-case-study-chinese-pdf.html",
    "https://insightbridge.global/publications/hbs-case-study-final.html",
    "https://insightbridge.global/publications/hbs-case-study-publication-grade.html",
    "https://insightbridge.global/publications/hn2-strategic-verticalism-polished.html",
    "https://insightbridge.global/publications/hn-a-vision2030-rms.html",
    "https://insightbridge.global/publications/hn-b-ota-direct-booking.html",
    "https://insightbridge.global/publications/ib-hotel-crisis-trust-hospitalitynet.html",
    "https://insightbridge.global/publications/imd-article-final-1.html",
    "https://insightbridge.global/publications/insightbridge-hotel-ai-market-report-2026.html",
    "https://insightbridge.global/publications/kinship-capability-and-cost-cross-strait-stability-2026-2030-v3.html",
    "https://insightbridge.global/publications/lian-he-zao-bao-tou-gao-qin-yuan-shi-li-yu-dai-jia-tai-hai-wen-ding-de-xian-shi-zhu-yi-xin-kuang-jia.html",
    "https://insightbridge.global/publications/lianhe-zaobao-cross-strait-realist-framework.html",
    "https://insightbridge.global/publications/mba-crisis-performance-ui-vs-core-code.html",
    "https://insightbridge.global/publications/mit-smr-jin-qian-mai-bu-dao-zhong-cheng-wan-zheng-zhong-wen-ban.html",
    "https://insightbridge.global/publications/mei-guo-jing-ji-1.html",
    "https://insightbridge.global/publications/nvidia-sage-case-teaching-note-v3.html",
    "https://insightbridge.global/publications/nvidia-sage-case-and-teaching-note.html",
    "https://insightbridge.global/publications/qin-yuan-neng-li-yu-cheng-ben-liang-an-wen-ding-fen-xi-kuang-jia-2026-2030-zhong-wen-ban.html",
    "https://insightbridge.global/publications/reclaiming-leadership-intuition-revised.html",
    "https://insightbridge.global/publications/san-yi-mei-yuan-de-guan-li-fu-zhai-jia-yuan-wen-hua-jing-shi-yin-tong-bo-shi.html",
    "https://insightbridge.global/publications/the-tyranny-of-mediocrity-why-our-systems-are-designed-to-exile-the-heroes-we-need-1.html",
    "https://insightbridge.global/publications/tourism-case-hospitality-2025.html",
    "https://insightbridge.global/publications/zhao-hui-ling-xiu-zhi-jue-zhong-wen-ban.html",
]

# ---------------------------------------------------------------------------
# Config — feel free to tweak.
# ---------------------------------------------------------------------------
SPN_ENDPOINT = "https://web.archive.org/save/"
PAUSE_SECONDS = 7.0           # spacing between requests (IA is friendly to ~1 req/6s)
REQUEST_TIMEOUT = 60          # each URL waits up to 60s for IA to finish crawling
MAX_RETRIES = 2               # try each URL up to 2 times before giving up
USER_AGENT = "InsightBridgeGlobal-WaybackSubmitter/1.0 (Mac)"

REPORT_PATH = "./archive_report.json"


def save_page_now(url: str) -> dict:
    """Submit one URL. Returns a dict describing the outcome.

    A successful Save Page Now request returns HTTP 200 or 302 with either:
      * A `Content-Location` header like `/web/YYYYMMDDHHMMSS/<url>` — snapshot
      * OR a body containing the snapshot URL
      * OR X-Archive-Wayback-Runtime-Error / X-Archive-Wayback-Liveweb-Error
        headers indicating IA couldn't fetch the URL
    """
    target = SPN_ENDPOINT + url
    req = urllib.request.Request(
        target,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as resp:
            status = resp.status
            location = resp.headers.get("Content-Location") or resp.headers.get("Location") or ""
            wb_error = (
                resp.headers.get("X-Archive-Wayback-Runtime-Error")
                or resp.headers.get("X-Archive-Wayback-Liveweb-Error")
                or ""
            )
            snapshot_url = ""
            if location.startswith("/web/"):
                snapshot_url = "https://web.archive.org" + location
            elif location.startswith("http"):
                snapshot_url = location

            ok = status in (200, 302) and not wb_error
            return {
                "url": url,
                "ok": ok,
                "status": status,
                "snapshot": snapshot_url,
                "wayback_error": wb_error,
            }
    except urllib.error.HTTPError as e:
        return {"url": url, "ok": False, "status": e.code, "error": f"HTTP {e.code}: {e.reason}"}
    except (urllib.error.URLError, http.client.RemoteDisconnected, TimeoutError) as e:
        return {"url": url, "ok": False, "status": 0, "error": f"network: {e}"}
    except Exception as e:  # pragma: no cover
        return {"url": url, "ok": False, "status": 0, "error": f"unexpected: {e}"}


def archive_with_retry(url: str) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        result = save_page_now(url)
        if result.get("ok"):
            return result
        transient = (
            result.get("status", 0) >= 500
            or "network" in result.get("error", "")
            or "TimeoutError" in result.get("error", "")
        )
        if attempt < MAX_RETRIES and transient:
            print(f"    retry {attempt}/{MAX_RETRIES - 1} in 15s ...")
            time.sleep(15)
            continue
        return result
    return result


def main() -> int:
    total = len(URL_LIST)
    print(f"InsightBridge Global — Wayback Machine batch archive")
    print(f"URLs to submit: {total}")
    print(f"Estimated runtime: ~{total * (PAUSE_SECONDS + 5) / 60:.1f} minutes")
    print("=" * 66)

    started = dt.datetime.now(dt.timezone.utc)
    results: list[dict] = []
    ok_count = 0

    for i, url in enumerate(URL_LIST, 1):
        print(f"[{i:2d}/{total}] {url}")
        r = archive_with_retry(url)
        results.append(r)
        if r.get("ok"):
            ok_count += 1
            snap = r.get("snapshot") or "(pending)"
            print(f"    ✓ archived  status={r.get('status')}  {snap}")
        else:
            err = r.get("error") or r.get("wayback_error") or "unknown"
            print(f"    ✗ failed   status={r.get('status')}  {err[:120]}")

        if i < total:
            time.sleep(PAUSE_SECONDS)

    finished = dt.datetime.now(dt.timezone.utc)
    duration = (finished - started).total_seconds()

    report = {
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round(duration, 1),
        "total_urls": total,
        "ok_count": ok_count,
        "fail_count": total - ok_count,
        "results": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 66)
    print(f"Done in {duration/60:.1f} min — {ok_count}/{total} archived successfully")
    print(f"Report written to: {REPORT_PATH}")
    if ok_count < total:
        print()
        print("Failed URLs (you can retry these by re-running the script):")
        for r in results:
            if not r.get("ok"):
                err = r.get("error") or r.get("wayback_error") or "unknown"
                print(f"  - {r['url']}  ({err[:80]})")

    return 0 if ok_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
