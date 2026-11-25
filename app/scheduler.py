from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select, func
import logging
import os

from app.core.db import engine
from app.core.models import MarketMetric, PriceData, NewsArticle, SocialMention

logger = logging.getLogger("evidlens.scheduler")

scheduler = BackgroundScheduler(timezone="Africa/Nairobi", job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300})
_scheduler_started = False

def _now():
    return datetime.now(timezone.utc)

def update_demand_scores():
    started = _now()
    logger.info("Running demand score update")
    try:
        with Session(engine) as session:
            yesterday = _now() - timedelta(days=1)
            rows = session.exec(select(PriceData.product_name, PriceData.county, PriceData.sector).distinct()).all()
            updated = 0
            for product, county, sector in rows:
                if not product or not county:
                    continue
                score = 0
                try:
                    price_data = session.exec(select(PriceData).where(PriceData.product_name == product, PriceData.county == county).order_by(PriceData.timestamp.desc()).limit(2)).all()
                    if len(price_data) == 2:
                        old_price = price_data[1].price or 0
                        if old_price:
                            change = (price_data[0].price - old_price) / old_price
                            if change > 0.1:
                                score += 40
                            elif change < -0.1:
                                score += 10
                    news_count = session.exec(select(func.count()).select_from(NewsArticle).where(NewsArticle.product == product, NewsArticle.timestamp > yesterday)).first() or 0
                    score += min(news_count * 30, 60)
                    social_count = session.exec(select(func.count()).select_from(SocialMention).where(SocialMention.product == product, SocialMention.timestamp > yesterday)).first() or 0
                    score += min((social_count // 100) * 10, 30)
                    score = max(0, min(score, 100))
                    metric = session.exec(select(MarketMetric).where(MarketMetric.product == product, MarketMetric.county == county)).first()
                    if metric:
                        metric.demand_score = score
                        if sector:
                            metric.sector = sector
                        metric.timestamp = _now()
                    else:
                        metric = MarketMetric(product=product, county=county, sector=sector or "", demand_score=score, timestamp=_now())
                        session.add(metric)
                    updated += 1
                except Exception as e:
                    logger.exception(f"Demand score failed for {product} / {county}: {e}")
                    session.rollback()
                    continue
            session.commit()
            logger.info(f"Demand scores updated: {updated} products in {( _now() - started).total_seconds():.1f}s")
    except Exception as e:
        logger.exception(f"Demand score job failed: {e}")

def run_price_scraper():
    try:
        from app.modules.lens_engine.service import scrape_kpin_prices
        scrape_kpin_prices()
        logger.info("Price scraper finished")
    except Exception as e:
        logger.exception(f"Price scraper failed: {e}")

def run_news_fetch():
    try:
        from app.modules.lens_engine.service import fetch_real_news
        fetch_real_news()
        logger.info("News fetch finished")
    except Exception as e:
        logger.exception(f"News fetch failed: {e}")

def run_social_fetch():
    try:
        from app.modules.lens_engine.service import fetch_real_tweets
        fetch_real_tweets()
        logger.info("Social fetch finished")
    except Exception as e:
        logger.exception(f"Social fetch failed: {e}")

def start_scheduler():
    global _scheduler_started
    if _scheduler_started:
        return scheduler
    if os.getenv("DISABLE_SCHEDULER", "") == "1":
        logger.info("Scheduler disabled via DISABLE_SCHEDULER=1")
        return scheduler
    if not scheduler.get_job("demand_score_job"):
        scheduler.add_job(update_demand_scores, IntervalTrigger(hours=1), id="demand_score_job", replace_existing=True)
    if not scheduler.get_job("price_scraper_job"):
        scheduler.add_job(run_price_scraper, CronTrigger(day_of_week="mon", hour=3, minute=0), id="price_scraper_job", replace_existing=True)
    if not scheduler.get_job("news_fetch_job"):
        scheduler.add_job(run_news_fetch, IntervalTrigger(hours=6), id="news_fetch_job", replace_existing=True)
    if not scheduler.get_job("social_fetch_job"):
        scheduler.add_job(run_social_fetch, IntervalTrigger(hours=1), id="social_fetch_job", replace_existing=True)
    if not scheduler.running:
        scheduler.start()
    _scheduler_started = True
    logger.info("EvidLens Scheduler started: Demand[1h] Price[Mon 3AM] News[6h] Social[1h]")
    return scheduler

def stop_scheduler():
    global _scheduler_started
    if scheduler.running:
        scheduler.shutdown(wait=False)
    _scheduler_started = False
