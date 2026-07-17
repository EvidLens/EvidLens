from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.services.base_service import BaseService
from app.models import Company
from app.core.config import settings
from app.core.db import redis_client
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import json

class CompetitiveEngineService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    async def company_deal_database(self, sector: str, company_name: str = None):
        cache_key = f"company_db:{sector}:{company_name}"
        cached = redis_client.get(cache_key)
        if cached: return json.loads(cached)
        q = self.db.query(Company).filter(Company.sector==sector)
        if company_name: q = q.filter(Company.name.ilike(f"%{company_name}%"))
        companies = q.all()
        brs = await self.call_api(f"https://brs.ecitizen.go.ke/api/companies?sector={sector}")
        for c in brs.get("data",[]):
            exists = self.db.query(Company).filter(Company.name==c["name"]).first()
            if not exists:
                self.db.add(Company(name=c["name"],sector=sector,country="Kenya",county=c.get("county"),directors=c.get("directors"),valuation=c.get("valuation")))
        self.db.commit()
        deals = await self.call_api(f"https://newsapi.org/v2/everything?q={sector} acquisition OR merger OR VC Kenya&apiKey={settings.NEWS_API_KEY}")
        result = {"companies":[c.__dict__ for c in companies],"deals":deals.get("articles",[])}
        redis_client.setex(cache_key, 3600, json.dumps(result))
        return result

    async def funding_tracker(self, sector: str, investor: str = None, date_range: str = "90d"):
        days = {"7d":7,"30d":30,"90d":90,"1y":365}[date_range]
        from_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        news = await self.call_api(f"https://newsapi.org/v2/everything?q={sector} funding investment Kenya&from={from_date}&apiKey={settings.NEWS_API_KEY}")
        funding = []
        for a in news.get("articles",[]):
            extracted = await self.call_groq(f"Extract JSON: founder, investor, amount_usd, date, exit. Article: {a['title']} {a['description']}")
            try:
                data = json.loads(extracted)
                if investor and investor.lower() in json.dumps(data).lower(): funding.append(data)
                elif not investor: funding.append(data)
            except: pass
        return {"funding_rounds": funding}

    async def digital_traffic_analyzer(self, competitor1: str, competitor2: str, date_range: str = "30d"):
        d1 = await self.call_api(f"https://api.similarweb.com/v1/website/{competitor1}/total-traffic-visits?start_date=2026-01-01&end_date=2026-04-01&api_key={settings.SIMILARWEB_KEY}")
        d2 = await self.call_api(f"https://api.similarweb.com/v1/website/{competitor2}/total-traffic-visits?start_date=2026-01-01&end_date=2026-04-01&api_key={settings.SIMILARWEB_KEY}")
        analysis = await self.call_groq(f"Compare {competitor1} vs {competitor2} traffic. Data1:{d1} Data2:{d2}. Give winner, gaps, recommendations.")
        return {"competitor1": d1, "competitor2": d2, "analysis": analysis}

    async def competitor_monitor(self, competitor: str, signal_type: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(f"https://{competitor}.com")
            content = await page.content()
            await browser.close()
        alerts = {}
        if signal_type == "price": alerts["price_change"] = "price" in content.lower()
        if signal_type == "product": alerts["new_product"] = "new" in content.lower()
        if signal_type == "job": alerts["job_post"] = "careers" in content.lower()
        summary = await self.call_groq(f"Monitor {competitor}. Signal:{signal_type}. Website content:{content[:2000]}. Return alerts JSON.")
        return {"competitor": competitor, "alerts": alerts, "ai_summary": summary}
