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

    scheduler.start()
    logger.info(
        "SEO scheduler started — recurring every %s hours", PUSH_INTERVAL_HOURS
    )

    # Run a one-shot catch-up check in the background
    asyncio.create_task(_maybe_catch_up(db))
