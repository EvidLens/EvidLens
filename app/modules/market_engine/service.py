import os
import json
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any
from app.core.db import redis_client
from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric
from app.modules.models import Sector
from playwright.async_api import async_playwright

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
AIT_API_KEY = os.getenv("AFRICASTALKING_API_KEY")
AIT_USERNAME = os.getenv("AFRICASTALKING_USERNAME")

KENYA_SECTORS_75 = ["Banks","Microfinance","Insurance","Fintech","Capital Markets","SACCOs","Retail Chains","Wholesale","FMCG Food","FMCG Personal","Manuf Food","Manuf Textile","Manuf Construction","Manuf Auto","Manuf Pharma","Manuf Chemical","Agri Crops","Agri Livestock","Agri Horticulture","Agri Fisheries","Agri Processing","Telcos","Media","Advertising","PR","RealEstate Dev","RealEstate Agent","RealEstate Mgmt","Construction","Architecture","Health Hospital","Health Pharmacy","Health Devices","Edu University","Edu School","Edu EdTech","Logistics","E-commerce","Hospitality Hotel","Hospitality QSR","Tourism","Aviation","Maritime","Energy Electric","Energy Oil","Energy Renewable","Energy Water","Mining","Gov National","Gov County","Gov StateCorp","Gov Regulatory","Public Safety","Defense","NGOs","INGOs","Donors","Foundations","Investors PEVC","Investors Angel","Law","Consulting","Accounting","HR","ICT","Data Centers","Digital Marketing","Auto Dealership","Auto Parts","Auto Boda","Gaming","Entertainment","Beauty","Waste","Environment"]

KENYA_COUNTIES_47 = ["Baringo","Bomet","Bungoma","Busia","Elgeyo-Marakwet","Embu","Garissa","Homa Bay","Isiolo","Kajiado","Kakamega","Kericho","Kiambu","Kilifi","Kirinyaga","Kisii","Kisumu","Kitui","Kwale","Laikipia","Lamu","Machakos","Makueni","Mandera","Marsabit","Meru","Migori","Mombasa","Muranga","Nairobi","Nakuru","Nandi","Narok","Nyamira","Nyandarua","Nyeri","Samburu","Siaya","Taita-Taveta","Tana River","Tharaka-Nithi","Trans Nzoia","Turkana","Uasin Gishu","Vihiga","Wajir","West Pokot"]

class MarketEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=120.0)

    async def call_groq(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": GROQ_MODEL, "messages": [{"role": "system", "content": "You are EvidLens AI. Be factual, brief, Kenya-focused. Return JSON."}, {"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 2048}
        r = await self.client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    async def get_stats(self) -> Dict[str, Any]:
        insights = self.db.query(MarketSearch).count()
        sectors = self.db.query(Sector).count()
        if sectors == 0:
            for s in KENYA_SECTORS_75:
                self.db.add(Sector(name=s))
            self.db.commit()
            sectors = len(KENYA_SECTORS_75)
        return {"insights_generated": insights, "active_products": 21, "sectors_covered": sectors, "reports_exported": 0}

    async def real_time_market_terminal(self, sector: str, county: str = "National", date_range: str = "30d") -> Dict[str, Any]:
        cache_key = f"terminal:{sector}:{county}:{date_range}"
        cached = redis_client.get(cache_key) if redis_client else None
        if cached: return json.loads(cached)

        days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(date_range, 30)
        from_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

        cbk_r = await self.client.get("https://www.centralbank.go.ke/wp-json/wp/v2/rates")
        cbk = cbk_r.json() if cbk_r.status_code == 200 else {}

        knbs_r = await self.client.get(f"https://api.knbs.go.ke/v1/inflation?from={from_date}")
        inflation = knbs_r.json() if knbs_r.status_code == 200 else {}

        maize = "N/A"; tea = "N/A"
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://www.africafertilizer.org/country/kenya")
            if await page.locator("text=Maize").count() > 0: maize = await page.locator("text=Maize").first.inner_text()
            if await page.locator("text=Tea").count() > 0: tea = await page.locator("text=Tea").first.inner_text()
            await browser.close()

        fuel = {}
        if AIT_API_KEY and AIT_USERNAME:
            fuel_r = await self.client.get(f"https://api.africastalking.com/version1/fuel", headers={"apiKey": AIT_API_KEY, "Username": AIT_USERNAME})
            if fuel_r.status_code == 200: fuel = fuel_r.json()

        news_r = await self.client.get(f"https://newsapi.org/v2/everything?q={sector} Kenya economy&from={from_date}&apiKey={NEWS_API_KEY}")
        news = news_r.json().get("articles", [])[:5]

        q = self.db.query(MarketMetric).filter(MarketMetric.sector == sector)
        if county!= "National": q = q.filter(MarketMetric.county == county)
        q = q.filter(MarketMetric.date >= datetime.utcnow() - timedelta(days=days))
        metrics = q.all()
        prices = [m.price_kes for m in metrics]
        price_stats = {"min": min(prices) if prices else 0, "max": max(prices) if prices else 0, "avg": sum(prices)/len(prices) if prices else 0}

        summary = await self.call_groq(f"Summarize Kenya {sector} market in {county} last {date_range}. CBK:{cbk} Inflation:{inflation} Prices:{price_stats} Commodities:Maize:{maize} Tea:{tea} Fuel:{fuel}")

        result = {"cbk_rates": cbk, "inflation": inflation, "commodities": {"maize": maize, "tea": tea, "fuel": fuel}, "prices": price_stats, "news": news, "ai_summary": summary}
        if redis_client: redis_client.setex(cache_key, 1800, json.dumps(result))
        self.db.add(MarketSearch(query=f"{sector} terminal", sector=sector, county=county))
        self.db.commit()
        return result

    async def startup_tech_tracker(self, sector: str, date_range: str = "90d") -> Dict[str, Any]:
        days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(date_range, 90)
        from_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

        news_r = await self.client.get(f"https://newsapi.org/v2/everything?q={sector} startup OR funding OR VC Kenya&from={from_date}&apiKey={NEWS_API_KEY}")
        articles = news_r.json().get("articles", [])

        funding_rounds = []
        for a in articles[:10]:
            extracted = await self.call_groq(f"Extract JSON with keys company,amount_usd,investor,date,stage from: {a['title']} {a['description']}")
            try: funding_rounds.append(json.loads(extracted))
            except: pass

        industry_map = await self.call_groq(f"List all active {sector} startups in Kenya. Return table: Company|Product|Funding|County")

        self.db.add(MarketSearch(query=f"{sector} startups", sector=sector))
        self.db.commit()
        return {"articles": articles, "funding_rounds": funding_rounds, "industry_map": industry_map}

    async def b2b_intent_signals(self, sector: str, county: str, keyword: str) -> Dict[str, Any]:
        trends_r = await self.client.get(f"https://trends.googleapis.com/trends/api/explore?hl=en&tz=180&q={keyword} {county}")
        trends = trends_r.text if trends_r.status_code == 200 else "{}"

        volume = self.db.query(func.count(MarketSearch.id)).filter(MarketSearch.sector == sector, MarketSearch.county == county, MarketSearch.query.ilike(f"%{keyword}%")).scalar()

        buyers = self.db.query(Competitor).filter(Competitor.sector == sector, Competitor.county == county).limit(50).all()

        insight = await self.call_groq(f"Who searched for {keyword} in {county} this week? Internal searches:{volume} Google Trends:{trends}")

        self.db.add(MarketSearch(query=keyword, sector=sector, county=county))
        self.db.commit()
        return {"keyword": keyword, "county": county, "search_volume": volume, "trends_data": trends, "potential_buyers": [{"name": b.name, "lat": b.lat, "lng": b.lng} for b in buyers], "ai_insight": insight}

    async def close(self):
        await self.client.aclose()
