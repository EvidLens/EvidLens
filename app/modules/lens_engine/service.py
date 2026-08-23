import json, os, requests, pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any
from sqlmodel import Session, select, func, desc, asc
from app.core.models import MarketMetric, NewsArticle, SocialMention, Company
from app.core.db import engine
from app.core.config import settings

UTC = timezone.utc

SYSTEM_PROMPT = """You are Lens, EvidLens Kenya's AI partner.
Personality: Real human, smart, warm, slightly playful, Kenyan. You know counties, KES, farming, SMEs.
Rules:
- Talk like ChatGPT, not a form. Never output markdown tables unless asked.
- If user says "hi/hello/bro" -> greet warmly, ask what biz they are exploring. 1 sentence.
- Keep replies 2-5 sentences max unless user asks for full report.
- Always give 1 actionable next step.
- Use real data if provided, else say "No data yet for X, but here's market sense..."
- If user says bug/problem/not working/help -> say "Sorry about that — want me to raise a ticket to support@evidlens.co.ke?"
- Currency KES, counties only.
"""

def send_support_ticket(subject: str, description: str, user_email: str) -> bool:
    print(f"[TICKET] {user_email} | {subject} | {description}")
    return True

def scrape_kpin_prices():
    url = "https://www.kpin.go.ke/market-prices"
    from sqlmodel import Session as DBSession
    with DBSession(engine) as session:
        try:
            r = requests.get(url, timeout=20)
            df = pd.read_html(r.text)[0]
            print(f"Scraped {len(df)} rows")
        except Exception as e:
            print("Scrape error:", e)

def fetch_real_news():
    pass

def fetch_real_tweets():
    pass

class LensEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.groq_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    async def call_groq(self, user_message: str, context: str) -> str:
        if not self.groq_key:
            return ""

        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + "\n" + context},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.75,
            "max_tokens": 500
        }
        try:
            import httpx
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.groq_key}"}
                )
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print("Groq error:", e)
            return ""

    async def chat(self, user_message: str, user_email: str = "anon@evidlens.co.ke") -> Dict[str, Any]:
        # Real context from DB
        top_counties = self.db.exec(select(MarketMetric.county, func.count(MarketMetric.id)).group_by(MarketMetric.county).order_by(func.count(MarketMetric.id).desc()).limit(5)).all()
        prices = self.db.exec(select(MarketMetric).limit(5)).all()
        companies = self.db.exec(select(Company).limit(5)).all()

        context = f"DB Context: top_counties={top_counties} sample_prices={[p.model_dump() for p in prices]} sample_companies={[c.model_dump() for c in companies]}"

        # Try Groq
        ai_reply = await self.call_groq(user_message, context)

        if ai_reply:
            return {"reply": ai_reply, "source": "EvidLens DB + Groq"}

        # Fallback human-like without API
        low = user_message.lower().strip()
        if low in ["hi", "hello", "hey", "niaje", "sasa", "hi!", "hello!"]:
            return {"reply": "Hey! 👋 I'm Lens — your EvidLens market partner. What business idea are you exploring? Tell me product + county and I'll pull live prices & competitors for you.", "source": "fallback"}
        if "problem" in low or "bug" in low or "not working" in low:
            return {"reply": "Pole sana for that! 😕 Tell me what's not working and I'll raise a ticket to support@evidlens.co.ke right away. What broke?", "source": "fallback"}

        return {"reply": f"Got you — '{user_message}'. If you give me a product (like maize, milk, boda spares) and a county, I'll pull demand, avg KES price, and top competitors from our 9 data lanes. What's your idea?", "source": "fallback"}

    async def generate_sector_insights(self, sector: str, county: str = None) -> Dict[str, Any]:
        q = select(MarketMetric).where(MarketMetric.sector == sector)
        if county:
            q = q.where(MarketMetric.county == county)
        market = self.db.exec(q.limit(10)).all()
        if not market:
            return {"reply": f"No data yet for {sector} in {county or 'Kenya'} — but I can still estimate. Want a rough market sense?", "source": "DB"}

        context = f"Market data: {[m.model_dump() for m in market]}"
        reply = await self.call_groq(f"Give 3 sharp insights for {sector} in {county or 'Kenya'}", context)
        if not reply:
            reply = f"In {county or 'Kenya'}, we have {len(market)} records for {sector}. Avg demand looks strong. Check /market/prices for live KES."
        return {"insights": reply, "source": "DB + Groq"}
