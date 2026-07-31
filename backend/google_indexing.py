"""
Google Indexing API integration.

Pushes URL_UPDATED notifications to https://indexing.googleapis.com/v3/urlNotifications:publish
so Google recrawls newly-published or updated URLs within minutes.

Setup (one-time, by the site owner):
  1. Google Cloud Console → create project → enable "Indexing API"
  2. IAM & Admin → Service Accounts → create new SA
  3. Add JSON key → download (keep secret)
  4. Google Search Console → Settings → Users & permissions → add the
     service-account email as **Owner** for the property (insightbridge.global)
  5. Put the JSON file on the server and set env var:
        GOOGLE_INDEXING_SA_JSON_PATH=/app/backend/secrets/gsc-indexing-sa.json

Quota: Google's default Indexing API quota is 200 URLs/day per project,
       100 requests/100 seconds. We throttle accordingly.
"""
from __future__ import annotations

import os
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

INDEXING_SCOPE = "https://www.googleapis.com/auth/indexing"
INDEXING_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"

SA_JSON_PATH = os.environ.get("GOOGLE_INDEXING_SA_JSON_PATH", "").strip()
SA_JSON_CONTENT = os.environ.get("GOOGLE_INDEXING_SA_JSON", "").strip()


def _is_configured() -> bool:
    return bool(SA_JSON_CONTENT) or (bool(SA_JSON_PATH) and os.path.exists(SA_JSON_PATH))


def _config_diagnostic() -> str:
    """Human-readable one-liner explaining WHY _is_configured() said False.

    SECURITY: This string is returned to public API callers via
    /api/seo/push. It MUST NEVER contain any env-var value verbatim —
    an operator may (by mistake) stuff the full service-account JSON
    into GOOGLE_INDEXING_SA_JSON_PATH. Only report set/unset + lengths.
    """
    env_len = len(SA_JSON_CONTENT)
    path_set = bool(SA_JSON_PATH)
    path_exists = path_set and os.path.exists(SA_JSON_PATH)
    if env_len:
        env_desc = f"set (len={env_len})"
    else:
        env_desc = "UNSET"
    if not path_set:
        path_desc = "UNSET"
    elif path_exists:
        path_desc = "set → file exists"
    else:
        path_desc = "set → file MISSING (value hidden)"
    return (
        f"Google Indexing not configured. "
        f"GOOGLE_INDEXING_SA_JSON env var: {env_desc}; "
        f"GOOGLE_INDEXING_SA_JSON_PATH: {path_desc}. "
        f"Fix: add GOOGLE_INDEXING_SA_JSON (full service-account JSON) to Backend Secrets and redeploy."
    )


def _get_access_token() -> str:
    """Refresh and return a bearer token for the Indexing API scope."""
    from google.oauth2 import service_account  # lazy import
    from google.auth.transport.requests import Request

    if SA_JSON_CONTENT:
        # Preferred: full service-account JSON via env var (no secret file in git)
        import json as _json
        creds = service_account.Credentials.from_service_account_info(
            _json.loads(SA_JSON_CONTENT), scopes=[INDEXING_SCOPE]
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            SA_JSON_PATH, scopes=[INDEXING_SCOPE]
        )
    creds.refresh(Request())
    if not creds.token:
        raise RuntimeError("Failed to obtain Google Indexing access token")
    return creds.token


def _publish_one(token: str, url: str, *, type_: str = "URL_UPDATED") -> Dict[str, Any]:
    """POST a single URL notification. Returns a dict describing the outcome."""
    import requests  # lazy import

    try:
        r = requests.post(
            INDEXING_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"url": url, "type": type_},
            timeout=15,
        )
        ok = r.status_code == 200
        try:
            body = r.json()
        except Exception:
            body = r.text[:300]
        return {
            "url": url,
            "ok": ok,
            "status_code": r.status_code,
            "response": body if not ok else "ok",
        }
    except Exception as e:  # network / DNS / etc
        return {"url": url, "ok": False, "status_code": 0, "response": str(e)[:300]}


def push_to_google(urls: List[str]) -> Dict[str, Any]:
    """Submit each URL individually to Google Indexing API.

    Returns the same shape as push_to_baidu / push_to_indexnow so it can
    plug into the existing run_push_urls/run_push_and_save aggregator.
    """
    engine_name = "google_indexing"

    if not _is_configured():
        return {
            "engine": engine_name,
            "ok": False,
            "skipped": _config_diagnostic(),
            "urls_submitted": 0,
        }

    if not urls:
        return {"engine": engine_name, "ok": False, "skipped": "no urls", "urls_submitted": 0}

    try:
        token = _get_access_token()
    except Exception as e:
        logger.exception("Google Indexing token refresh failed")
        return {"engine": engine_name, "ok": False, "error": str(e), "urls_submitted": 0}

    per_url: List[Dict[str, Any]] = []
    succeeded = 0
    # Per Google's published rate limit (100 req / 100s), we sleep 1.05s
    # between calls — still finishes 24 URLs in ~25s, well under request timeout.
    for i, u in enumerate(urls):
        out = _publish_one(token, u)
        per_url.append(out)
        if out["ok"]:
            succeeded += 1
        if i < len(urls) - 1:
            time.sleep(1.05)

    return {
        "engine": engine_name,
        "ok": succeeded > 0,
        "status_code": 200 if succeeded == len(urls) else 207,
        "urls_submitted": len(urls),
        "succeeded": succeeded,
        "failed": len(urls) - succeeded,
        "per_url": per_url[:50],  # cap log size
    }
