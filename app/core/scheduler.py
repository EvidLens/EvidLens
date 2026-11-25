import logging
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select, func
from datetime import datetime, timezone

from app.core.config import settings
from app.core.db import engine
from app.core.models import KenyaLensBusiness

logger = logging.getLogger(__name__)
UTC = timezone.utc

scheduler = BackgroundScheduler(timezone="Africa/Nairobi")
_scheduler_started = False

def safe_job(job_func, job_name: str):
    try:
        logger.info("[%s] Running...", job_name)
        job_func()
        logger.info("[%s] Success", job_name)
    except Exception as e:
        logger.exception("[%s] FAILED: %s", job_name, e)
        traceback.print_exc()

def init_db():
    import app.core.models
    import app.modules.auth.models
    try:
        import app.modules.wallet.models
    except Exception:
        pass
    try:
        import app.modules.report_builder.models
    except Exception:
        pass
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    logger.info("DB tables checked/created")

def seed_data():
    with Session(engine) as session:
        count = session.exec(select(func.count(KenyaLensBusiness.id))).one() or 0
        if count == 0:
            logger.info("DB is empty. No hardcoded seed data added. Use /api/import to load businesses.")

def run_kpin_job():
    try:
        from app.modules.jobs.scrapers import scrape_kpin_prices
    except Exception as e:
        logger.warning("KPIN scraper not available, skipping: %s", e)
        return
    scrape_kpin_prices()

def run_news_job():
    try:
        from app.modules.jobs.scrapers import fetch_real_news
    except Exception as e:
        logger.warning("News scraper not available, skipping: %s", e)
        return
    fetch_real_news()

def run_tweets_job():
    try:
        from app.modules.jobs.scrapers import fetch_real_tweets
    except Exception as e:
        logger.warning("Tweets scraper not available, skipping: %s", e)
        return
    fetch_real_tweets()

def run_expiry_job():
    from app.core.models import UserSubscription
    with Session(engine) as session:
        now = datetime.now(UTC)
        stmt = select(UserSubscription).where(
            UserSubscription.status == "active",
            UserSubscription.expires_at != None,
            UserSubscription.expires_at < now,
        )
        expired = session.exec(stmt).all()
        for sub in expired:
            sub.status = "expired"
            session.add(sub)
        if expired:
            session.commit()
            logger.info("Expired %d subscriptions", len(expired))

def start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return scheduler
    if getattr(settings, "DISABLE_SCHEDULER", False):
        logger.info("Scheduler disabled via DISABLE_SCHEDULER")
        return scheduler
    jobs = [
        ("kpin_scrape", run_kpin_job, "KPIN", getattr(settings, "KPIN_SCRAPE_HOUR", 6), getattr(settings, "KPIN_SCRAPE_MINUTE", 0)),
        ("news_scrape", run_news_job, "NEWS", getattr(settings, "NEWS_SCRAPE_HOUR", 7), getattr(settings, "NEWS_SCRAPE_MINUTE", 0)),
        ("tweets_scrape", run_tweets_job, "TWEETS", getattr(settings, "TWEETS_SCRAPE_HOUR", 8), getattr(settings, "TWEETS_SCRAPE_MINUTE", 0)),
        ("expiry_cleanup", run_expiry_job, "EXPIRY", 0, 5),
    ]
    for job_id, func, name, hour, minute in jobs:
        scheduler.add_job(
            lambda f=func, n=name: safe_job(f, n),
            CronTrigger(hour=hour, minute=minute),
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
    scheduler.start()
    _scheduler_started = True
    logger.info("Scheduler started. Timezone: Africa/Nairobi")
    return scheduler

def shutdown_scheduler():
    global _scheduler_started
    if scheduler.running:
        scheduler.shutdown(wait=False)
    _scheduler_started = False
    logger.info("Scheduler shut down")
