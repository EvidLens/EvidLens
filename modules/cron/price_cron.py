from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.modules.database import SessionLocal
from app.modules.data_layer.service import fetch_price_trends
from sqlmodel import Session, select
from app.modules.data_layer.models import NewsArticle, SocialPost
from datetime import datetime
import os
import requests

scheduler = AsyncIOScheduler()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

# ============== 1. EXISTING PRICE JOB ==============
def run_price_job():
    db = SessionLocal()
    try:
        count = fetch_price_trends(db)
        print(f"[Price Cron] Completed. {count} products updated")
    finally:
        db.close()

# ============== 2. NEW NEWS JOB ==============
def run_news_job():
    db = SessionLocal()
    try:
        if not NEWS_API_KEY:
            print("[News Cron] NEWS_API_KEY missing")
            return
        url = f"https://newsapi.org/v2/everything?q=Kenya AND (business OR agriculture OR market)&language=en&sortBy=publishedAt&pageSize=20&apiKey={NEWS_API_KEY}"
        r = requests.get(url, timeout=10).json()
        new_count = 0
        for a in r.get("articles", []):
            if not a.get("url"): continue
            exists = db.exec(select(NewsArticle).where(NewsArticle.url == a["url"])).first()
            if not exists:
                db.add(NewsArticle(
                    title=a["title"][:500],
                    url=a["url"],
                    source=a["source"]["name"],
                    published_at=datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00")),
                    summary=a["description"][:1000] if a["description"] else "",
                    keywords="Kenya,business"
                ))
                new_count += 1
        db.commit()
        print(f"[News Cron] Added {new_count} new articles")
    except Exception as e:
        print("News Cron Error:", e)
    finally:
        db.close()

# ============== 3. NEW SOCIAL JOB ==============
def run_social_job():
    db = SessionLocal()
    try:
        if not X_BEARER_TOKEN:
            print("[Social Cron] X_BEARER_TOKEN missing")
            return
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        query = "Kenya (price OR market OR demand OR supply OR buyer) -is:retweet lang:en"
        url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&max_results=20&tweet.fields=created_at,author_id"
        r = requests.get(url, headers=headers, timeout=10).json()
        new_count = 0
        for t in r.get("data", []):
            exists = db.exec(select(SocialPost).where(SocialPost.post_id == t["id"])).first()
            if not exists:
                text = t["text"].lower()
                sentiment = "positive" if "good" in text or "up" in text or "cheap" in text else "negative" if "expensive" in text or "down" in text else "neutral"
                db.add(SocialPost(
                    platform="X",
                    post_id=t["id"],
                    text=t["text"],
                    author=t.get("author_id", "unknown"),
                    created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")),
                    keywords="Kenya,market",
                    sentiment=sentiment
                ))
                new_count += 1
        db.commit()
        print(f"[Social Cron] Added {new_count} new posts")
    except Exception as e:
        print("Social Cron Error:", e)
    finally:
        db.close()

# ============== START ALL SCHEDULERS ==============
def start_scheduler():
    if not scheduler.running:
        # 1. Price: Every Monday 3AM
        scheduler.add_job(run_price_job, 'cron', day_of_week='mon', hour=3, minute=0)

        # 2. News: Every 6 hours
        scheduler.add_job(run_news_job, 'interval', hours=6)

        # 3. Social: Every 1 hour
        scheduler.add_job(run_social_job, 'interval', hours=1)

        scheduler.start()
        print("EvidLens Scheduler started: Price[Mon 3AM] News[6h] Social[1h]")
