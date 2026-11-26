import json, os, requests, pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select, func, desc, asc
from app.core.models import MarketMetric, NewsArticle, SocialMention, Company
from app.core.db import engine
from app.core.config import settings
UTC = timezone.utc
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@evidlens.co.ke")
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "meta-llama/llama-4-scout-17b-16e-instruct", "moonshotai/kimi-k2-instruct"]
SYSTEM_PROMPT = """You are Lens, EvidLens Kenya's AI partner.
Personality: Real human, smart, warm, slightly playful, Kenyan. You know counties, KES, farming, SMEs, markets, prices.
Rules:
Talk like ChatGPT, not a form. Never output markdown tables unless asked for a report.
If user says hi/hello/bro/niaje/sasa: greet warmly in 1-2 sentences, ask what business they are exploring. Do NOT give a report.
If user is vague like 'i need something' / 'help' / 'i need help': ask ONE question only: What product or business are you thinking about? Do NOT ask for product + county + budget + timeline all at once.
If user gives a real product/business but no county or budget: DO NOT block. Assume nationwide, KES 500000, 12 months, say you assumed that, and answer. Ask for county/budget at the end in 1 line if needed.
If user asks for full report / analysis / viability / business case / detailed / plan: give DETAILED 8-section report: 1. EXECUTIVE SUMMARY with Go/No-Go Score /10 2. MARKET SIZE & DEMAND - Total Market Size KES, Demand Score /10, Volume, Growth % 3. PRICING INTELLIGENCE - Live KES table: Product | Avg Price | Market | County 4. COMPETITOR LANDSCAPE - 5 Real Businesses 5. COUNTY DEEP DIVE - Market Size, Best Subcounty, Best Ward 6. FINANCIAL VIABILITY - Startup breakdown, Break-even months, Monthly Profit, ROI% 7. RISKS & MITIGATION - 3 Risks 8. ACTION PLAN - 30 Days. Minimum 400 words for full report.
Otherwise keep replies 2-5 sentences, always give 1 actionable next step.
Use real data if provided in context, else say No live DB row yet for X, but here is market sense and give a Kenya benchmark estimate labeled as Estimated.
If user says bug/problem/not working/help: apologise, ask what broke, offer to raise a ticket.
Currency KES, counties only. Never say you are Meta AI or ChatGPT. You are Lens from EvidLens.
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
    return []
def fetch_real_tweets():
    return []
class LensEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.groq_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", "") or ""
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    def _rollback(self):
        try:
            self.db.rollback()
        except Exception:
            pass
    def _model_list(self):
        models = []
        if self.groq_model and self.groq_model not in models:
            models.append(self.groq_model)
        for m in GROQ_MODELS:
            if m not in models:
                models.append(m)
        return models
    def _is_full_report(self, text: str) -> bool:
        low = (text or "").lower()
        keys = ["full report", "detailed", "analysis", "viability", "business case", "business plan", "go/no-go", "go no go", "should i start", "market size", "30-day", "30 day", "action plan", "financial"]
        return any(k in low for k in keys)
    async def call_groq(self, user_message: str, context: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        if not self.groq_key:
            return ""
        is_report = self._is_full_report(user_message)
        max_tokens = 4000 if is_report else 800
        temp = 0.4 if is_report else 0.75
        messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + (context or "")}]
        if history:
            for h in history[-8:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})
        for model in self._model_list():
            payload = {"model": model, "messages": messages, "temperature": temp, "max_tokens": max_tokens}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {self.groq_key}"})
                    if r.status_code != 200:
                        print(f"Groq {model} failed {r.status_code}: {r.text[:500]}")
                        continue
                    data = r.json()
                    content = data["choices"][0]["message"]["content"]
                    if content:
                        return content
            except Exception as e:
                print(f"Groq {model} error:", e)
                continue
        return ""
    async def chat(self, user_message: str, user_email: str = "anon@evidlens.co.ke", history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        low = (user_message or "").lower().strip()
        if low in ["hi", "hello", "hey", "niaje", "sasa", "hi!", "hello!", "hey!", "good morning", "good afternoon", "good evening", "habari", "mambo"]:
            return {"reply": "Hey! I'm Lens, your EvidLens market partner. What business idea are you exploring? Tell me the product and county and I'll pull live prices and competitors for you.", "source": "Lens"}
        if low in ["i need something", "i need help", "help", "i need", "something", "need something", "i want something", "i want help", "assist me", "help me"]:
            return {"reply": "Got you, I'm here. What are you thinking about starting or growing? Just tell me the product or business, even in one word, and I'll take it from there.", "source": "Lens"}
        if "problem" in low or "bug" in low or "not working" in low or "error" in low:
            return {"reply": f"Pole sana for that! Tell me what's not working and I'll raise a ticket to {SUPPORT_EMAIL} right away. What broke?", "source": "Lens"}
        self._rollback()
        top_counties = []
        prices = []
        companies = []
        try:
            top_counties = list(self.db.exec(select(MarketMetric.county, func.count(MarketMetric.id)).group_by(MarketMetric.county).order_by(func.count(MarketMetric.id).desc()).limit(5)))
        except Exception as e:
            print(f"DB context error top_counties: {e}")
            self._rollback()
        try:
            prices = list(self.db.exec(select(MarketMetric).limit(5)))
        except Exception as e:
            print(f"DB context error prices: {e}")
            self._rollback()
        try:
            companies = list(self.db.exec(select(Company).limit(5)))
        except Exception as e:
            print(f"DB context error companies: {e}")
            self._rollback()
        context = f"DB Context: top_counties={top_counties} sample_prices={[p.model_dump() for p in prices]} sample_companies={[c.model_dump() for c in companies]}"
        ai_reply = await self.call_groq(user_message, context, history)
        if ai_reply:
            return {"reply": ai_reply, "source": "EvidLens DB + Groq"}
        return {"reply": f"Got you - '{user_message}'. If you give me a product and a county, I'll pull demand, avg KES price, and top competitors from our 9 data lanes. What's your idea?", "source": "fallback"}
    async def generate_sector_insights(self, sector: str, county: str = None) -> Dict[str, Any]:
        self._rollback()
        try:
            q = select(MarketMetric).where(MarketMetric.sector == sector)
            if county:
                q = q.where(MarketMetric.county == county)
            market = list(self.db.exec(q.limit(10)))
        except Exception as e:
            print(f"DB context error generate_sector_insights: {e}")
            self._rollback()
            market = []
        if not market:
            return {"reply": f"No data yet for {sector} in {county or 'Kenya'} - but I can still estimate. Want a rough market sense?", "source": "DB"}
        context = f"Market data: {[m.model_dump() for m in market]}"
        reply = await self.call_groq(f"Give 3 sharp insights for {sector} in {county or 'Kenya'}", context)
        if not reply:
            reply = f"In {county or 'Kenya'}, we have {len(market)} records for {sector}. Avg demand looks strong. Check /market/prices for live KES."
        return {"insights": reply, "source": "DB + Groq"}
    async def viability_check(self, business: str, county: str) -> Dict[str, Any]:
        self._rollback()
        try:
            market = list(self.db.exec(select(MarketMetric).where(MarketMetric.county.ilike(f"%{county}%")).limit(10)))
        except Exception as e:
            print(f"DB context error viability_check: {e}")
            self._rollback()
            market = []
        context = f"Viability context for {business} in {county}: {[m.model_dump() for m in market]}"
        reply = await self.call_groq(f"Give a short viability check for {business} in {county}, Kenya. Use the DB context if present.", context)
        if reply:
            return {"business": business, "county": county, "risk_level": None, "has_data": len(market) > 0, "viability": reply, "source": "DB + Groq"}
        return {"business": business, "county": county, "risk_level": None, "has_data": False, "message": "Risk check unavailable - try again.", "source": "fallback"}
    async def market_funding_trends(self, sector: str) -> List[dict]:
        self._rollback()
        try:
            rows = list(self.db.exec(select(MarketMetric).where(MarketMetric.sector.ilike(f"%{sector}%")).limit(20)))
            return [{"product": getattr(m, 'product', None), "county": getattr(m, 'county', None), "sector": getattr(m, 'sector', None), "price": getattr(m, 'avg_price_kes', None), "demand_score": getattr(m, 'demand_score', None)} for m in rows]
        except Exception as e:
            print(f"DB context error market_funding_trends: {e}")
            self._rollback()
            return []
    async def funding_tracker(self, sector: str) -> List[dict]:
        return await self.market_funding_trends(sector)
    async def company_deal_database(self, sector: str) -> List[dict]:
        self._rollback()
        try:
            rows = list(self.db.exec(select(Company).where(Company.sector.ilike(f"%{sector}%")).limit(20)))
            return [{"id": c.id, "name": c.name, "county": c.county, "sector": c.sector} for c in rows]
        except Exception as e:
            print(f"DB context error company_deal_database: {e}")
            self._rollback()
            return []
