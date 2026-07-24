"""
app/services/scheduler.py

Automatic weekly pipeline runs -- uses APScheduler instead of Celery.

WHY APScheduler INSTEAD OF CELERY:
The original brief mentioned Celery + Redis for background jobs, and
Redis is already in your stack. But Celery's worker/beat processes are
notoriously fragile to set up and run reliably on Windows (the platform
you're developing on) -- file-descriptor and multiprocessing quirks
cause frequent silent failures. APScheduler is a pure-Python library
that runs an in-process scheduler alongside your existing FastAPI app --
no extra worker process, no Windows-specific pain, and it's more than
enough for "run this once a week per brand."

If you later deploy to a Linux server and want true distributed background
jobs (multiple workers, retries, task queues), migrating to Celery at
that point is straightforward -- this isn't a dead end, just the right
tool for right now.

HOW IT WORKS:
On FastAPI startup, this starts a background scheduler that wakes up
once a day and checks: which brands have auto_run_enabled=True AND
today matches their auto_run_day AND they haven't already run today?
For each match, it triggers the same run_full_pipeline() used by the
manual "Run Pipeline" button.
"""

import asyncio
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

DAY_NAME_TO_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

scheduler = AsyncIOScheduler()


async def check_and_run_scheduled_brands():
    """
    Runs once a day (see start_scheduler). Checks every brand with
    auto_run_enabled=True -- if today matches their chosen day and they
    haven't already run today, trigger the full pipeline for them.
    """
    from app.models.database import SessionLocal, Brand
    from app.services.pipeline import run_full_pipeline

    db = SessionLocal()
    try:
        today_index = date.today().weekday()  # 0=Monday .. 6=Sunday
        today = date.today()

        brands = db.query(Brand).filter(Brand.auto_run_enabled == True).all()  # noqa: E712

        for brand in brands:
            scheduled_day_index = DAY_NAME_TO_INDEX.get((brand.auto_run_day or "monday").lower(), 0)

            if scheduled_day_index != today_index:
                continue

            if brand.last_auto_run and brand.last_auto_run.date() == today:
                continue  # already ran today, skip

            print(f"\n⏰ Auto-run triggered for brand: {brand.name} ({brand.domain})")
            try:
                # run_full_pipeline expects its own db session internally
                # via get_db in the API layer -- here we pass this session
                # directly since we're calling it outside a request context.
                result = await run_full_pipeline(str(brand.id), db)
                print(f"   ✅ Auto-run result: {result}")
            except Exception as e:
                print(f"   ❌ Auto-run failed for {brand.name}: {e}")

            brand.last_auto_run = datetime.utcnow()
            db.commit()

    finally:
        db.close()


def start_scheduler():
    """Call this once from app startup (main.py)."""
    # Runs once a day at 6:00 AM server time -- checks all brands and
    # fires any whose scheduled day matches today.
    scheduler.add_job(
        lambda: asyncio.create_task(check_and_run_scheduled_brands()),
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_schedule_check",
        replace_existing=True,
    )
    scheduler.start()
    print("✅ Auto-run scheduler started (checks daily at 6:00 AM)")


def stop_scheduler():
    """Call this from app shutdown."""
    if scheduler.running:
        scheduler.shutdown()