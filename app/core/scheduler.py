from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select, func
import traceback

from app.core.config import settings
from app.core.db import engine
from app.modules.core.models import KenyaLensBusiness
from app.modules.jobs.scrapers import scrape_kpin_prices, fetch_real_news, fetch_real_tweets

# ====== SCHEDULER INSTANCE ======
scheduler = BackgroundScheduler(timezone="Africa/Nairobi")

def safe_job(job_func, job_name: str):
    """Wrapper so 1 job failing doesn't kill others"""
    try:
        print(f"[{job_name}] Running...")
        job_func()
        print(f"[{job_name}] Success")
    except Exception as e:
        print(f"[{job_name}] FAILED: {e}")
        traceback.print_exc()

def init_db():
    """Create tables on startup"""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    print("DB tables checked/created")

def seed_data():
    """No hardcoded businesses. DB starts empty"""
    with Session(engine) as session:
        count = session.exec(select(func.count(KenyaLensBusiness.id))).one()
        if count == 0:
            print("DB is empty. No hardcoded seed data added. Use /api/import to load businesses.")

def start_scheduler():
    """Register all cron jobs and start scheduler"""
    # Jobs - Using CronTrigger so we respect settings.py times
    scheduler.add_job(
        lambda: safe_job(scrape_kpin_prices, "KPIN"),
        CronTrigger(hour=settings.KPIN_SCRAPE_HOUR, minute=settings.KPIN_SCRAPE_MINUTE),
        id="kpin_scrape", replace_existing=True
    )
    scheduler.add_job(
        lambda: safe_job(fetch_real_news, "NEWS"),
        CronTrigger(hour=settings.NEWS_SCRAPE_HOUR, minute=settings.NEWS_SCRAPE_MINUTE),
        id="news_scrape", replace_existing=True
    )
    scheduler.add_job(
        lambda: safe_job(fetch_real_tweets, "TWEETS"),
        CronTrigger(hour=settings.TWEETS_SCRAPE_HOUR, minute=settings.TWEETS_SCRAPE_MINUTE),
        id="tweets_scrape", replace_existing=True
    )
    scheduler.start()
    print(f"Scheduler started. Timezone: Africa/Nairobi")

def shutdown_scheduler():
    """Graceful shutdown"""
    scheduler.shutdown()
    print("Scheduler shut down")
