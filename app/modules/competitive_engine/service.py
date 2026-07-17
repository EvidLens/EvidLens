import os
import json
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, List, Optional
from app.modules.db import redis_client
from app.modules.competitive_engine.models import Company, FundingDeal, TrafficSnapshot
from playwright.async_api import async_playwright

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
SIMILARWEB_KEY = os.getenv("SIMILARWEB_KEY")

async def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY: return "Set GROQ_API_KEY"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": GROQ_MODEL, "messages": [{"role": "system", "content": "You are Lens, EvidLens AI for Kenya."}, {"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 500})
        return r.json()["choices"][0]["message"]["content"]

async def call_api(url: str) -> Dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        return r.json() if r.status_code == 200 else {}

# 4. COMPANY & DEAL DATABASE
async def company_deal_database(db: Session, sector: str, company_name: str = None) -> Dict[str, Any]:
    cache_key = f"company_db:{sector}:{company_name}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached: return json.loads(cached)

    q = db.query(Company).filter(Company.sector==sector)
    if company_name: q = q.filter(Company.name.ilike(f"%{company_name}%"))
    companies = q.limit(50).all()

    brs = await call_api(f"https://brs.ecitizen.go.ke/api/companies?sector={sector}") # Mock BRS
    for c in brs.get("data",[]):
        exists = db.query(Company).filter(Company.name==c["name"]).first()
        if not exists:
            db.add(Company(name=c["name"],sector=sector,country="Kenya",county=c.get("county"),directors=c.get("directors"),valuation=c.get("valuation")))
    db.commit()

    deals = await call_api(f"https://newsapi.org/v2/everything?q={sector} acquisition OR merger OR VC Kenya&apiKey={NEWS_API_KEY}&pageSize=5")

    result = {
        "companies":[{"name":c.name,"county":c.county,"valuation":c.valuation,"directors":c.directors} for c in companies],
        "deals": deals.get("articles",[])
    }
    if redis_client: redis_client.setex(cache_key, 3600, json.dumps(result))
    return result

# 5. FUNDING TRACKER
async def funding_tracker(db: Session, sector: str, investor: str = None, date_range: str = "90d") -> Dict[str, Any]:
    days = {"7d":7,"30d":30,"90d":90,"1y":365}[date_range]
    from_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
    news = await call_api(f"https://newsapi.org/v2/everything?q={sector} funding investment Kenya&from={from_date}&apiKey={NEWS_API_KEY}&pageSize=10")
    funding = []
    for a in news.get("articles",[]):
        extracted = await call_groq(f"Extract JSON with keys: founder, investor, amount_usd, date, company. Article: {a['title']} {a['description']}")
        try:
            data = json.loads(extracted)
            if investor and investor.lower() in json.dumps(data).lower(): funding.append(data)
            elif not investor: funding.append(data)
        except: pass
    return {"funding_rounds": funding, "count": len(funding)}

# 6. DIGITAL TRAFFIC ANALYZER
async def digital_traffic_analyzer(db: Session, competitor1: str, competitor2: str, date_range: str = "30d") -> Dict[str, Any]:
    d1 = await call_api(f"https://api.similarweb.com/v1/website/{competitor1}/total-traffic-visits?start_date=2026-01-01&end_date=2026-04-01&api_key={SIMILARWEB_KEY}")
    d2 = await call_api(f"https://api.similarweb.com/v1/website/{competitor2}/total-traffic-visits?start_date=2026-01-01&end_date=2026-04-01&api_key={SIMILARWEB_KEY}")
    analysis = await call_groq(f"Compare {competitor1} vs {competitor2} traffic. Data1:{json.dumps(d1)[:500]} Data2:{json.dumps(d2)[:500]}. Give winner, traffic gaps, 3 recommendations. Under 80 words.")
    return {"competitor1": d1.get("visits",0), "competitor2": d2.get("visits",0), "analysis": analysis}

# 7. COMPETITOR MONITOR
async def competitor_monitor(db: Session, competitor: str, signal_type: str) -> Dict[str, Any]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://{competitor}.com", timeout=10000)
        content = await page.content()
        await browser.close()

    alerts = {}
    if signal_type == "price": alerts["price_change"] = "price" in content.lower() or "ksh" in content.lower()
    if signal_type == "product": alerts["new_product"] = "new" in content.lower() or "launch" in content.lower()
    if signal_type == "job": alerts["job_post"] = "careers" in content.lower() or "jobs" in content.lower()
    if signal_type == "ad": alerts["new_ad"] = "ad" in content.lower()

    summary = await call_groq(f"Monitor {competitor}. Signal:{signal_type}. Website content:{content[:2000]}. Return 3 key changes as JSON.")
    return {"competitor": competitor, "signal": signal_type, "alerts": alerts, "ai_summary": summary}
