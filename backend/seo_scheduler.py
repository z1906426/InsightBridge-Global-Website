"""
APScheduler setup — runs SEO push every 24 hours.

Behaviour:
  - On startup, look up the latest push in MongoDB.
    - If none, OR if it was >24 h ago, run a push immediately ("catch-up").
  - Then schedule subsequent pushes every 24 hours.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from seo_push import run_push_and_save

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
PUSH_INTERVAL_HOURS = 24


async def _do_push(db) -> None:
    try:
        await run_push_and_save(db)
    except Exception:
        logger.exception("Scheduled SEO push failed")


async def _maybe_catch_up(db) -> None:
    """If we haven't pushed in 72 h, run now."""
    try:
        last = await db.seo_pushes.find_one(sort=[("timestamp", -1)])
        if not last:
            logger.info("SEO push: no prior records → catch-up push now")
            await _do_push(db)
            return
        last_ts = datetime.fromisoformat(last["timestamp"])
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_ts
        if delta > timedelta(hours=PUSH_INTERVAL_HOURS):
            logger.info(
                "SEO push: last push %s ago (> %sh) → catch-up push now",
                delta, PUSH_INTERVAL_HOURS,
            )
            await _do_push(db)
        else:
            logger.info(
                "SEO push: last push %s ago (≤ %sh) → no catch-up needed",
                delta, PUSH_INTERVAL_HOURS,
            )
    except Exception:
        logger.exception("Catch-up check failed")


def start_scheduler(db) -> None:
    """Idempotent: safe to call multiple times. Registers the recurring job."""
    if scheduler.running:
        return

    async def job():
        await _do_push(db)

    scheduler.add_job(
        job,
        IntervalTrigger(hours=PUSH_INTERVAL_HOURS),
        id="seo_push_job",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc) + timedelta(hours=PUSH_INTERVAL_HOURS),
    )

    # Also register sister-headline refresh every 6h
    try:
        from sister_articles import refresh_sister_headlines, REFRESH_INTERVAL_HOURS

        async def headlines_job():
            try:
                await refresh_sister_headlines(db)
            except Exception:
                logger.exception("Headlines refresh job failed")

        scheduler.add_job(
            headlines_job,
            IntervalTrigger(hours=REFRESH_INTERVAL_HOURS),
            id="sister_headlines_job",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=1),  # warm up shortly after boot
        )
        logger.info(
            "Sister-headlines refresh registered — every %s hours",
            REFRESH_INTERVAL_HOURS,
        )
    except Exception:
        logger.exception("Could not register sister headlines job")

    # Weekly press-citation stats sync (trust strip counters)
    try:
        from press_stats import refresh_press_stats, REFRESH_INTERVAL_HOURS as PRESS_HOURS

        async def press_stats_job():
            try:
                await refresh_press_stats(db)
            except Exception:
                logger.exception("Press stats refresh job failed")

        scheduler.add_job(
            press_stats_job,
            IntervalTrigger(hours=PRESS_HOURS),
            id="press_stats_job",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=2),
        )
        logger.info("Press-stats refresh registered — every %s hours", PRESS_HOURS)
    except Exception:
        logger.exception("Could not register press stats job")

    # Daily RSS feed regeneration — keeps /rss.xml <lastBuildDate> fresh so
    # crawlers know the feed is alive and worth re-polling.
    try:
        from rss_feed import write_rss

        async def rss_job():
            try:
                # write_rss is sync (small I/O); run in threadpool to avoid
                # blocking the event loop if the disk is slow.
                await asyncio.to_thread(write_rss)
            except Exception:
                logger.exception("RSS regeneration job failed")

        scheduler.add_job(
            rss_job,
            IntervalTrigger(hours=24),
            id="rss_feed_job",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=3),
        )
        logger.info("RSS feed regeneration registered — every 24 hours")
    except Exception:
        logger.exception("Could not register RSS feed job")

    # Weekly Wayback Machine "Save Page Now" — creates a permanent, third-party
    # verified archive of our main URLs so we always have a citable snapshot.
    # Also archives every citation URL from the sister-site press page so the
    # 📎 archived badges on our trust strip actually populate.
    try:
        from wayback import save_pages_now
        from seo_push import get_urls as _get_main_urls

        async def wayback_job():
            try:
                urls: list[str] = list(_get_main_urls())
                # Add all citation URLs from the latest press_stats snapshot
                try:
                    snap = await db.press_stats_snapshot.find_one({"_id": "latest"})
                    if snap and snap.get("list"):
                        for it in snap["list"]:
                            u = it.get("url")
                            if u and u not in urls:
                                urls.append(u)
                except Exception:
                    logger.exception("Could not append citation URLs to wayback batch")

                # Run the (blocking) HTTP calls in a threadpool so we don't
                # stall the event loop. The helper already spaces requests
                # by 6.5s to stay under Wayback's ~10/min anonymous rate.
                results = await asyncio.to_thread(save_pages_now, urls)
                ok = sum(1 for r in results if r.get("ok"))
                logger.info("Wayback archive job: %d/%d URLs snapshotted", ok, len(urls))
                # Persist a tiny record so /api/wayback/status can show
                # when the last archive run happened.
                try:
                    await db.wayback_runs.insert_one({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "urls_count": len(urls),
                        "ok_count": ok,
                        "results": results,
                    })
                except Exception:
                    logger.exception("Failed to persist wayback run record")
            except Exception:
                logger.exception("Wayback archive job failed")

        scheduler.add_job(
            wayback_job,
            IntervalTrigger(hours=168),  # weekly
            id="wayback_archive_job",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(minutes=5),  # first run 5min after boot
        )
        logger.info("Wayback archive job registered — every 168 hours (weekly)")
    except Exception:
        logger.exception("Could not register Wayback archive job")

    scheduler.start()
    logger.info(
        "SEO scheduler started — recurring every %s hours", PUSH_INTERVAL_HOURS
    )

    # Run a one-shot catch-up check in the background
    asyncio.create_task(_maybe_catch_up(db))
