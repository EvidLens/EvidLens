import json
import pandas as pd
import requests
import tweepy
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlmodel import select, func, desc, asc

from app.services.base_service import BaseService # 1. INHERIT
from app.modules.database import MarketMetric, NewsArticle, SocialMention, Session as DBSession, engine
from app.core.config import settings # 2. Use settings not os.getenv

SYSTEM_PROMPT = """You are EvidLens AI. You give market insights for Kenyan farmers and SMEs.
Rules:
1. Be concise. Max 4 sentences. Data-driven. Use KES and Counties.
2. If user asks "how do I...", guide them step by step through the app features.
3. If user says "problem", "bug", "not working", "help", "support" -> You MUST call raise_ticket function. End with: "Should I raise a ticket for you?"
4. If no data, say "No data yet for X county".
5. Always give 1 actionable next step.
"""

def send_support_ticket(subject: str, description: str, user_email: str) -> bool:
    print(f"[TICKET] From: {user_email} | Subject: {subject} | {description}")
    return True

def get_lat_lng(county: str):
    return -1.286389, 36.817223

def apply_sort(q, model, sort_by: str, order: str):
    if not sort_by or not hasattr(model, sort_by): return q
    col = getattr(model, sort_by)
    return q.order_by(desc(col) if order == "desc" else asc(col))

def scrape_kpin_prices():
    url = "https://www.kpin.go.ke/market-prices"
    with DBSession(engine) as session:
        try:
            r = requests.get(url, timeout=30)
            df = pd.read_html(r.text)[0]
            df.columns = ['date', 'county', 'market', 'product', 'price', 'unit']
            df['price'] = df['price'].astype(str).str.replace(',', '').astype(float)
            today = datetime.utcnow().date()
            for _, row in df.iterrows():
                existing = session.exec(select(MarketMetric).where(
                    MarketMetric.product == row['product'],
                    MarketMetric.company_name == row['market'],
                    func.date(MarketMetric.created_at) == today
                )).first()
                if not existing:
                    session.add(MarketMetric(
                        product=row['product'], company_name=row['market'],
                        avg_price_kes=row['price'], county=row['county'], sector=row['unit']
                    ))
            session.commit()
        except Exception as e: print("Scrape error:", e)

def fetch_real_news():
    if not settings.NEWS_API_KEY: return
    with DBSession(engine) as db:
        url = f"https://newsapi.org/v2/everything?q=Kenya&language=en&pageSize=100&apiKey={settings.NEWS_API_KEY}"
        try:
            data = requests.get(url, timeout=30).json()
            for article in data.get("articles", []):
                if not article["title"]: continue
                existing = db.exec(select(NewsArticle).where(NewsArticle.title == article["title"])).first()
                if not existing:
                    db.add(NewsArticle(title=article["title"], source=article["source"]["name"], summary=article["description"] or ""))
            db.commit()
        except Exception as e: print("News error:", e)

def fetch_real_tweets():
    if not settings.X_BEARER_TOKEN: return
    with DBSession(engine) as db:
        client_t = tweepy.Client(bearer_token=settings.X_BEARER_TOKEN)
        for query in ["Kenya price", "Kenya maize", "Kenya fuel"]:
            try:
                tweets = client_t.search_recent_tweets(query=query, max_results=50)
                if tweets.data:
                    for t in tweets.data:
                        existing = db.exec(select(SocialMention).where(SocialMention.text == t.text)).first()
                        if not existing: db.add(SocialMention(text=t.text, platform="Twitter"))
                db.commit()
            except Exception as e: print("Twitter error:", e)

class LensEngineService(BaseService): # 3. INHERIT
    def __init__(self, db: Session):
        super().__init__(db)

    async def call_groq_with_tools(self, user_message: str, context: str, user_email: str) -> str:
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + context},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2, "max_tokens": 350,
            "tools": [{"type": "function", "function": {
                "name": "raise_ticket", "description": "Raise a support ticket to EvidLens team",
                "parameters": {"type": "object", "properties": {
                    "subject": {"type": "string"}, "description": {"type": "string"}
                }, "required": ["subject", "description"]}
            }}],
            "tool_choice": "auto"
        }
        try:
            # 4. USE self.client from BaseService instead of creating new one
            r = await self.client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"})
            r.raise_for_status()
            message = r.json()["choices"][0]["message"]
        except Exception:
            return "AI summary unavailable"

        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                if tool_call["function"]["name"] == "raise_ticket":
                    args = json.loads(tool_call["function"]["arguments"])
                    sent = send_support_ticket(args['subject'], args['description'], user_email)
                    return "Ticket raised successfully. Our team at support@evidlens.co.ke will reply within 24hrs." if sent else "Could not send ticket. Please email us directly at support@evidlens.co.ke"
        return message.get("content", "No response")

    async def chat(self, user_message: str, user_email: str) -> Dict[str, Any]:
        stats = {"total_businesses": 0}
        market = [m.dict() for m in self.db.exec(select(MarketMetric).limit(5)).all()]
        context = f"\nData Available: Stats={json.dumps(stats)} Market={json.dumps(market)}"
        reply = await self.call_groq_with_tools(user_message, context, user_email)
        return {"reply": reply, "source": "EvidLens DB + Groq"}

    async def generate_sector_insights(self, sector: str, county: str = None) -> Dict[str, Any]:
        q = select(MarketMetric).where(MarketMetric.sector == sector)
        if county: q = q.where(MarketMetric.county == county)
        market = [m.dict() for m in self.db.exec(q.limit(10)).all()]
        if not market: return {"reply": f"No data yet for {county or sector} county", "source": "EvidLens DB"}
        context = f"\nData Available: Market={json.dumps(market)}"
        reply = await self.call_groq_with_tools(f"Give 3 insights for {sector} in {county or 'Kenya'}", context, "")
        return {"insights": reply, "source": "EvidLens DB + Groq"}
