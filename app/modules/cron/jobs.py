import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlmodel import Session, select
from dotenv import load_dotenv

from app.core.db import engine
from app.core.models import MarketMetric, NewsArticle, SocialMention, KenyaLensBusiness

load_dotenv()
UTC = timezone.utc

KPIN_URL = "https://www.kpin.co.ke/api/prices" # Real KPIN endpoint
NEWS_API_KEY = os.getenv("NEWS_API_KEY") # from newsapi.org
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN") # from developer.twitter.com

async def _save_market_metrics(db: Session, items: List[Dict[str, Any]]):
    for item in items:
        exists = db.exec(
            select(MarketMetric).where(
                MarketMetric.product == item["product"],
                MarketMetric.county == item["county"],
                MarketMetric.source == "KPIN"
            ).order_by(MarketMetric.created_at.desc())
        ).first()
        
        metric = MarketMetric(
            product=item["product"],
            category=item.get("category", "FMCG"),
            sector=item.get("sector", "Food & Beverage"),
            county=item["county"],
            sub_county=item.get("sub_county"),
            avg_price_kes=item["price"],
            min_price_kes=item.get("min_price"),
            max_price_kes=item.get("max_price"),
            demand_score=item.get("demand_score", 50.0),
            supply_score=item.get("supply_score", 50.0),
            source="KPIN",
            source_url="https://www.kpin.co.ke",
            created_at=datetime.now(UTC)
        )
        if exists:
            exists.avg_price_kes = metric.avg_price_kes
            exists.updated_at = datetime.now(UTC)
        else:
            db.add(metric)
    db.commit()

async def _save_news(db: Session, articles: List[Dict[str, Any]]):
    for a in articles:
        exists = db.exec(select(NewsArticle).where(NewsArticle.url == a["url"])).first()
        if not exists:
            db.add(NewsArticle(
                title=a["title"],
                source=a["source"],
                url=a["url"],
                summary=a.get("description"),
                category=a.get("category", "General"),
                published_at=a.get("published_at", datetime.now(UTC)),
                created_at=datetime.now(UTC)
            ))
    db.commit()

async def _save_social(db: Session, tweets: List[Dict[str, Any]]):
    for t in tweets:
        exists = db.exec(select(SocialMention).where(SocialMention.platform_id == t["id"])).first()
        if not exists:
            sentiment = "neutral"
            content_lower = t["text"].lower()
            if any(w in content_lower for w in ["good", "love", "best", "cheap"]): sentiment = "positive"
            if any(w in content_lower for w in ["bad", "expensive", "hate", "worst"]): sentiment = "negative"

            db.add(SocialMention(
                platform="twitter",
                platform_id=t["id"],
                author=t["author"],
                content=t["text"],
                sentiment=sentiment,
                sector=t.get("sector"),
                created_at=t.get("created_at", datetime.now(UTC))
            ))
    db.commit()

def scrape_kpin_prices():
    """Scrape real KPIN prices for Kenya. Runs daily 3AM"""
    print("Starting KPIN scrape...")
    with Session(engine) as db, httpx.Client(timeout=30.0) as client:
        try:
            res = client.get(KPIN_URL)
            res.raise_for_status()
            data = res.json() # Expect: [{"product": "Maize 2kg", "county": "Nairobi", "price": 180}]
            
            items = []
            for d in data:
                items.append({
                    "product": d["product_name"],
                    "county": d["county"],
                    "category": d.get("category"),
                    "price": float(d["average_price"]),
                    "min_price": float(d.get("min_price", d["average_price"])),
                    "max_price": float(d.get("max_price", d["average_price"]))
                })
            
            import asyncio
            asyncio.run(_save_market_metrics(db, items))
            print(f"KPIN: Saved {len(items)} price points")
        except Exception as e:
            print(f"KPIN scrape failed: {e}")

def fetch_real_news():
    """Fetch real Kenya news from NewsAPI. Runs daily 4AM"""
    if not NEWS_API_KEY:
        print("NEWS_API_KEY not set. Skipping news fetch.")
        return
    
    print("Starting News fetch...")
    with Session(engine) as db, httpx.Client(timeout=30.0) as client:
        try:
            yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"https://newsapi.org/v2/everything?q=Kenya OR business OR economy&from={yesterday}&sortBy=publishedAt&language=en&pageSize=100&apiKey={NEWS_API_KEY}"
            res = client.get(url)
            res.raise_for_status()
            data = res.json()
            
            articles = []
            for a in data.get("articles", []):
                # Categorize
                title = a["title"].lower()
                category = "General"
                if "policy" in title or "government" in title: category = "Policy"
                if "funding" in title or "invest" in title: category = "Funding"
                if "agriculture" in title: category = "Agriculture"
                
                articles.append({
                    "title": a["title"],
                    "source": a["source"]["name"],
                    "url": a["url"],
                    "description": a["description"],
                    "category": category,
                    "published_at": datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                })
            
            import asyncio
            asyncio.run(_save_news(db, articles))
            print(f"NEWS: Saved {len(articles)} articles")
        except Exception as e:
            print(f"News fetch failed: {e}")

def fetch_real_tweets():
    """Fetch real tweets about Kenya business. Runs daily 5AM"""
    if not TWITTER_BEARER_TOKEN:
        print("TWITTER_BEARER_TOKEN not set. Skipping tweets fetch.")
        return

    print("Starting Twitter fetch...")
    with Session(engine) as db, httpx.Client(timeout=30.0) as client:
        try:
            headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
            query = 'Kenya (business OR startup OR economy OR "SACCO" OR "M-Pesa") -is:retweet lang:en'
            url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&tweet.fields=created_at,author_id&user.fields=name,username&expansions=author_id&max_results=100"
            res = client.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            
            tweets = []
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
            for t in data.get("data", []):
                author = users.get(t["author_id"], {}).get("username", "unknown")
                tweets.append({
                    "id": t["id"],
                    "text": t["text"],
                    "author": author,
                    "created_at": datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
                })
            
            import asyncio
            asyncio.run(_save_social(db, tweets))
            print(f"TWEETS: Saved {len(tweets)} tweets")
        except Exception as e:
            print(f"Twitter fetch failed: {e}")
