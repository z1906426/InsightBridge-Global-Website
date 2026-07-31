from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


# ====================================================================
# SEO push endpoints — manual trigger + status (scheduled job runs
# automatically every 72 h via seo_scheduler.start_scheduler at startup)
# ====================================================================
from seo_push import run_push_and_save, run_push_urls  # noqa: E402
from publications import extract_publication_urls  # noqa: E402
from calculators import (  # noqa: E402
    POLARISInput, POLARISResult, compute_polaris,
    OTAInput, OTAResult, compute_ota,
)
from sister_articles import (  # noqa: E402
    refresh_sister_headlines, get_brief_for_main_site,
)

@api_router.post("/seo/push")
async def trigger_seo_push():
    """Manually trigger a push to all search engines now."""
    return await run_push_and_save(db)

@api_router.get("/seo/publications")
async def list_publication_urls():
    """List the publication URLs auto-extracted from the homepage."""
    urls = extract_publication_urls()
    return {"count": len(urls), "urls": urls}

@api_router.post("/seo/push-publications")
async def push_publication_urls():
    """Push the Research & Publications URLs (extracted from index.html)
    to IndexNow + Baidu. Baidu is capped at 10 URLs to respect daily quota."""
    urls = extract_publication_urls()
    return await run_push_urls(db, urls, label="publications")

@api_router.get("/seo/status")
async def seo_status():
    """Return the last SEO push record + scheduler health."""
    last = await db.seo_pushes.find_one(sort=[("timestamp", -1)], projection={"_id": 0})
    count = await db.seo_pushes.count_documents({})
    return {
        "total_pushes": count,
        "last_push": last,
        "interval_hours": 24,
    }


@api_router.get("/seo/google-indexing/status")
async def google_indexing_status():
    """Read-only diagnostic for the Google Indexing API auth wiring.

    Never returns secret material — only reports whether the two supported
    env vars are set and, if a path is given, whether the referenced file
    exists on the container. Useful for verifying the Emergent Secrets
    injection into the backend container after a redeploy.
    """
    import os as _os
    env_content = _os.environ.get("GOOGLE_INDEXING_SA_JSON", "")
    env_path = _os.environ.get("GOOGLE_INDEXING_SA_JSON_PATH", "").strip()
    from google_indexing import _is_configured as _cfg
    return {
        "configured": _cfg(),
        "sources": {
            "GOOGLE_INDEXING_SA_JSON": {
                "set": bool(env_content),
                "length": len(env_content),
                "starts_with_brace": env_content.strip().startswith("{") if env_content else False,
            },
            "GOOGLE_INDEXING_SA_JSON_PATH": {
                "set": bool(env_path),
                "value": env_path or None,
                "file_exists": bool(env_path) and _os.path.exists(env_path),
            },
        },
        "hint": (
            "OK — configured. Ready to push."
            if _cfg()
            else "Add GOOGLE_INDEXING_SA_JSON (full service-account JSON) to Backend Secrets in Manage Publishing, then redeploy."
        ),
    }

@api_router.get("/seo/history")
async def seo_history(limit: int = 20):
    """Return the most recent SEO push records (newest first)."""
    cursor = db.seo_pushes.find(
        {},
        projection={
            "_id": 0, "timestamp": 1, "label": 1, "urls_count": 1,
            "baidu_urls_count": 1, "results": 1, "ok_all": 1,
        },
    ).sort("timestamp", -1).limit(min(max(limit, 1), 100))
    items = await cursor.to_list(length=None)
    # Slim down per-url payload to keep response small
    for it in items:
        for r in it.get("results") or []:
            r.pop("per_url", None)
    return {"count": len(items), "items": items}


@api_router.get("/seo/coverage")
async def seo_coverage(days: int = 30):
    """Aggregated push-coverage stats: per-engine success rate + daily timeline."""
    from datetime import datetime, timedelta, timezone as tz
    days = max(1, min(days, 180))
    since = datetime.now(tz.utc) - timedelta(days=days)
    since_iso = since.isoformat()

    cursor = db.seo_pushes.find(
        {"timestamp": {"$gte": since_iso}},
        projection={"_id": 0, "timestamp": 1, "results": 1, "ok_all": 1,
                    "urls_count": 1, "baidu_urls_count": 1},
    ).sort("timestamp", 1)
    records = await cursor.to_list(length=None)

    ENGINES = ("baidu", "indexnow", "google", "seznam")
    per_engine = {e: {"attempts": 0, "ok": 0, "fail": 0,
                      "last_ok_at": None, "last_error": None} for e in ENGINES}

    day_bucket = {}
    for rec in records:
        ts = rec.get("timestamp", "")
        date = ts[:10] if ts else "unknown"
        b = day_bucket.setdefault(date, {"pushes": 0, "ok_all": 0})
        b["pushes"] += 1
        if rec.get("ok_all"):
            b["ok_all"] += 1
        for r in (rec.get("results") or []):
            engine = r.get("engine", "").lower()
            # Normalize: `google_indexing` → `google` (keeps the summary keys clean)
            if engine == "google_indexing":
                engine = "google"
            if engine not in per_engine:
                continue
            per_engine[engine]["attempts"] += 1
            if r.get("ok"):
                per_engine[engine]["ok"] += 1
                per_engine[engine]["last_ok_at"] = ts
            else:
                per_engine[engine]["fail"] += 1
                err = r.get("error") or r.get("skipped") or f"HTTP {r.get('status_code')}"
                per_engine[engine]["last_error"] = str(err)[:200]

    for e in ENGINES:
        stats = per_engine[e]
        stats["success_rate"] = (
            round(stats["ok"] / stats["attempts"], 4) if stats["attempts"] else None
        )

    total = len(records)
    ok_all_count = sum(1 for r in records if r.get("ok_all"))
    distinct_urls = sum(r.get("urls_count") or 0 for r in records)

    last_push_at = records[-1]["timestamp"] if records else None
    next_push_at = None
    if last_push_at:
        try:
            next_push_at = (
                datetime.fromisoformat(last_push_at.replace("Z", "+00:00"))
                + timedelta(hours=24)
            ).isoformat()
        except Exception:
            pass

    timeline = []
    day_cursor = since.date()
    end_day = datetime.now(tz.utc).date()
    while day_cursor <= end_day:
        key = day_cursor.isoformat()
        cell = day_bucket.get(key, {"pushes": 0, "ok_all": 0})
        timeline.append({"date": key, **cell})
        day_cursor += timedelta(days=1)

    return {
        "window_days": days,
        "summary": {
            "total_pushes": total,
            "ok_all_rate": round(ok_all_count / total, 4) if total else None,
            "urls_pushed_cumulative": distinct_urls,
            "last_push_at": last_push_at,
            "next_push_at": next_push_at,
        },
        "per_engine": per_engine,
        "timeline": timeline,
    }


# ====================================================================
# Server-side calculators — protect proprietary formulas from
# client-side inspection. Frontend posts inputs, receives results.
# ====================================================================

@api_router.post("/calc/polaris", response_model=POLARISResult)
async def calc_polaris(payload: POLARISInput):
    """POLARIS hotel pricing calculator — 5 demand-driver weights server-side."""
    return compute_polaris(payload)


# Backwards-compat alias for the legacy /calc/mare path (kept until all
# frontend deploys have flipped to /calc/polaris). Safe to remove later.
@api_router.post("/calc/mare", response_model=POLARISResult, include_in_schema=False)
async def calc_mare_legacy(payload: POLARISInput):
    return compute_polaris(payload)


@api_router.post("/calc/ota", response_model=OTAResult)
async def calc_ota(payload: OTAInput):
    """OTA True Cost calculator — 4-layer fee stack server-side."""
    return compute_ota(payload)


# ====================================================================
# Sister-site headlines — for the main-site hero brief sidebar.
# Refreshed every 6 hours by APScheduler.
# ====================================================================

@api_router.get("/headlines")
async def headlines(limit: int = 7):
    """Return the newest sister-site articles for the hero brief."""
    items = await get_brief_for_main_site(db, limit=min(max(limit, 1), 20))
    return {"count": len(items), "items": items}


@api_router.post("/headlines/refresh")
async def headlines_refresh():
    """Manually re-fetch sister-site articles now (out-of-band)."""
    snap = await refresh_sister_headlines(db)
    return {"ok": True, "count": snap.get("count", 0)}


# ====================================================================
# Press citation stats — syncs the "Cited & Syndicated Worldwide"
# trust strip counters from the sister site's /press page. Weekly.
# ====================================================================
from press_stats import refresh_press_stats, get_press_stats, get_press_citations


@api_router.get("/press/stats")
async def press_stats():
    """Cached citation counters (citations / countries / languages)."""
    return await get_press_stats(db)


@api_router.get("/press/citations")
async def press_citations():
    """Cached counters + full ordered citation list for the main-site trust strip."""
    return await get_press_citations(db)


@api_router.post("/press/stats/refresh")
async def press_stats_refresh():
    """Manually re-scrape the sister site's /press page now."""
    return await refresh_press_stats(db)


@api_router.post("/wayback/archive-now")
async def wayback_archive_now():
    """Manually trigger Save Page Now for all main URLs + every citation URL
    from the latest press_stats snapshot. Mirrors the weekly scheduled job so
    a fresh press-stats refresh can be pushed to Internet Archive on demand."""
    import asyncio
    from wayback import save_pages_now
    from seo_push import get_urls
    urls: list[str] = list(get_urls())
    main_count = len(urls)
    # Append citation URLs from the latest press_stats_snapshot (deduped)
    try:
        snap = await db.press_stats_snapshot.find_one({"_id": "latest"})
        if snap and snap.get("list"):
            for it in snap["list"]:
                u = it.get("url")
                if u and u not in urls:
                    urls.append(u)
    except Exception:
        logger.exception("Could not append citation URLs to wayback batch")
    citations_count = len(urls) - main_count
    results = await asyncio.to_thread(save_pages_now, urls)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "urls_count": len(urls),
        "main_urls_count": main_count,
        "citation_urls_count": citations_count,
        "ok_count": sum(1 for r in results if r.get("ok")),
        "results": results,
        "manual": True,
    }
    try:
        await db.wayback_runs.insert_one(dict(record))
    except Exception:
        logger.exception("Failed to persist wayback run record")
    return record


@api_router.get("/wayback/status")
async def wayback_status():
    """Show the last N Wayback archive runs."""
    cursor = db.wayback_runs.find({}, projection={"_id": 0, "results": 0}).sort("timestamp", -1).limit(10)
    runs = await cursor.to_list(length=10)
    return {"count": len(runs), "runs": runs}


# ====================================================================
# Main-site RSS feed — writes /app/frontend/site/rss.xml. Search-engine
# crawlers (Google, Bing, Baidu, Yandex, etc.) can subscribe and re-crawl
# on their own cadence. Regenerated daily by APScheduler; /rss.xml is
# also submitted via IndexNow + Baidu + Google on the SEO push cycle.
# ====================================================================
from rss_feed import write_rss, ensure_rss_exists  # noqa: E402


@api_router.post("/rss/refresh")
async def rss_refresh():
    """Manually regenerate the main-site RSS feed at /rss.xml."""
    return write_rss()


@api_router.get("/rss/status")
async def rss_status():
    """Return metadata about the generated feed (path, size, last mtime)."""
    from pathlib import Path
    from rss_feed import RSS_OUTPUT_PATH, SITE_URL

    p: Path = RSS_OUTPUT_PATH
    if not p.exists():
        return {"exists": False, "url": f"{SITE_URL}/rss.xml"}
    stat = p.stat()
    return {
        "exists": True,
        "url": f"{SITE_URL}/rss.xml",
        "bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# GEO Playbook Step 6 — AI TL;DR + alias map endpoints.
# Serves the 6-field synthesis (Core Problem / Theoretical Solution /
# Empirical Metric × EN+ZH) that populate_geo_static.py writes to
# /app/frontend/site/_data/geo_fields.json. The aliases/map endpoint is a
# thin stub for static-site parity — path IS the slug so we return an empty
# but well-formed mapping for now, expandable when we start renaming files.
# ---------------------------------------------------------------------------
_GEO_JSON_PATH = Path("/app/frontend/site/_data/geo_fields.json")


def _read_geo_data() -> dict:
    if not _GEO_JSON_PATH.exists():
        return {}
    try:
        return json.loads(_GEO_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Failed to read geo_fields.json: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Alias computation — every publication PDF/DOCX filename stem that differs
# from the kebab-case canonical slug is a valid legacy alias, plus a small
# hand-curated table of past slug renames (e.g., the xian-incident shortening
# that was flagged by the testing agent on iteration 3).
# ---------------------------------------------------------------------------
_PUBLICATIONS_DIR = Path("/app/frontend/site/publications")

# Hand-maintained legacy-slug map — add entries here when we rename an article
# that already had inbound links or citations.
_LEGACY_SLUG_RENAMES = {
    "xian-incident": "xian-incident-republican-china-politics",
}


def _slugify(stem: str) -> str:
    """Mirror of the same function in build_publication_landings.py."""
    import re as _re
    s = stem.lower()
    s = _re.sub(r"[_\s]+", "-", s)
    s = _re.sub(r"[^a-z0-9\-]+", "", s)
    return _re.sub(r"-+", "-", s).strip("-")


def _compute_aliases(canonicals: dict) -> dict:
    """Return legacy-or-alternative → canonical-slug for every article whose
    canonical slug differs from a plausible legacy form. Sources:

      1. Publications: original PDF/DOCX filename stem (Title_Case with
         underscores) — any crawler or hand-typed URL using the raw filename
         should resolve to the kebab-case landing page slug.
      2. `_LEGACY_SLUG_RENAMES` — manually curated table of past renames.
    """
    aliases: dict[str, str] = {}
    canonical_slugs = set(canonicals.keys())

    if _PUBLICATIONS_DIR.exists():
        for p in _PUBLICATIONS_DIR.iterdir():
            if p.suffix.lower() not in (".pdf", ".docx"):
                continue
            stem = p.stem
            canonical = _slugify(stem)
            if canonical not in canonical_slugs:
                continue
            # Underscore-preserved case-preserved form (raw filename stem)
            if stem != canonical and stem not in aliases:
                aliases[stem] = canonical
            # Lower-cased underscore form
            stem_lower = stem.lower()
            if stem_lower != canonical and stem_lower not in aliases:
                aliases[stem_lower] = canonical

    for legacy, canonical in _LEGACY_SLUG_RENAMES.items():
        if canonical in canonical_slugs:
            aliases[legacy] = canonical

    return aliases


@api_router.get("/articles/{slug}/ai-tldr")
async def article_ai_tldr(slug: str):
    """Structured 6-field AI synthesis for the given article slug.

    Designed for LLM crawlers (GPTBot, ClaudeBot, PerplexityBot, …) that
    prefer JSON over HTML. Mirrors what the visible AI Synthesis Reference
    Block on the article page already shows. If `slug` is a legacy alias
    (e.g., original PDF filename stem), the endpoint resolves it to the
    canonical slug transparently — no 404, no redirect chain.
    """
    data = _read_geo_data()
    resolved_slug = slug
    entry = data.get(slug)
    if not entry:
        canonicals = {s: e.get("canonical") for s, e in data.items()}
        alias_map = _compute_aliases(canonicals)
        canonical_slug = alias_map.get(slug)
        if canonical_slug:
            resolved_slug = canonical_slug
            entry = data.get(canonical_slug)
    if not entry:
        raise HTTPException(status_code=404, detail=f"No AI synthesis for slug '{slug}'")
    fields = entry.get("fields", {})
    return {
        "slug": resolved_slug,
        "requested_slug": slug,
        "resolved_via_alias": resolved_slug != slug,
        "canonical": entry.get("canonical"),
        "canonical_url": entry.get("canonical"),  # alias field for API-name parity
        "path": entry.get("path"),
        "updated_at": entry.get("updated_at"),
        "core_problem": {
            "en": fields.get("core_problem_en", ""),
            "zh": fields.get("core_problem_zh", ""),
        },
        "theoretical_solution": {
            "en": fields.get("theoretical_solution_en", ""),
            "zh": fields.get("theoretical_solution_zh", ""),
        },
        "empirical_metric": {
            "en": fields.get("empirical_metric_en", ""),
            "zh": fields.get("empirical_metric_zh", ""),
        },
    }


@api_router.get("/articles/aliases/map")
async def article_aliases_map():
    """Legacy-slug → canonical-slug mapping.

    Populated from two sources:
      * Original PDF/DOCX filename stems (Title_Case, underscores) for every
        publication whose landing page uses the kebab-case slugified form.
        Crawlers or bookmark URLs typed against the raw filename resolve here.
      * A hand-curated table of past article-slug renames (see
        `_LEGACY_SLUG_RENAMES`) so old inbound links still work.
    """
    data = _read_geo_data()
    canonicals = {slug: entry.get("canonical") for slug, entry in data.items()}
    aliases = _compute_aliases(canonicals)
    return {
        "count": len(aliases),
        "alias_count": len(aliases),
        "canonical_count": len(canonicals),
        "aliases": aliases,
        "canonicals": canonicals,
    }


@api_router.post("/seo/push-all-geo")
async def push_all_geo():
    """One-shot: push EVERY canonical URL registered in geo_fields.json
    (main articles + publications landing pages) plus the publications hub,
    sitemap and RSS to all four search engines (IndexNow / Baidu / Google
    Indexing / Seznam). Use after a big batch GEO enrichment.
    """
    from seo_push import run_push_urls, get_urls as _core_urls
    data = _read_geo_data()
    urls: list[str] = []
    # Priority pages first — homepage, RSS, executive bio, hub, sitemap
    urls.extend(_core_urls())
    urls.append("https://insightbridge.global/publications/")
    urls.append("https://insightbridge.global/sitemap.xml")
    # Every GEO-registered canonical URL
    for slug, entry in data.items():
        canonical = entry.get("canonical")
        if canonical:
            urls.append(canonical)
    # De-dup while preserving order
    seen: set[str] = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    return await run_push_urls(db, unique_urls, label="geo-batch-all-2026-02")


@api_router.post("/wayback/archive-all-geo")
async def wayback_archive_all_geo():
    """One-shot: archive EVERY canonical URL registered in geo_fields.json
    to the Internet Archive Wayback Machine, in addition to main pages.
    Use after a big batch to guarantee the AI-citation snapshots are
    preserved for future retrieval."""
    import asyncio
    from wayback import save_pages_now
    from seo_push import get_urls as _core_urls
    data = _read_geo_data()
    urls: list[str] = list(_core_urls())
    urls.append("https://insightbridge.global/publications/")
    for slug, entry in data.items():
        canonical = entry.get("canonical")
        if canonical:
            urls.append(canonical)
    # De-dup
    seen: set[str] = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    main_count = len(_core_urls())
    results = await asyncio.to_thread(save_pages_now, unique_urls)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "label": "geo-batch-all-2026-02",
        "urls_count": len(unique_urls),
        "main_urls_count": main_count,
        "geo_urls_count": len(unique_urls) - main_count,
        "ok_count": sum(1 for r in results if r.get("ok")),
        "results": results,
        "manual": True,
    }
    try:
        await db.wayback_runs.insert_one(dict(record))
    except Exception:
        logger.exception("Failed to persist wayback run record (geo-all)")
    return record






# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Start the SEO push scheduler on app startup
@app.on_event("startup")
async def start_seo_scheduler():
    try:
        # Ensure /rss.xml exists on disk before scheduler / first push.
        try:
            ensure_rss_exists()
        except Exception:
            logger.exception("Failed to ensure rss.xml exists on startup")

        from seo_scheduler import start_scheduler
        start_scheduler(db)
        logger.info("SEO push scheduler initialised (every 24h)")
    except Exception:
        logger.exception("Failed to start SEO scheduler")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()