# app/modules/market_engine/service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.services.base_service import BaseService
from app.modules.market_engine.models import MarketSearch, Competitor
from app.modules.consumer_voice.service import get_sentiment_summary
from app.modules.data_layer.service import get_demand_signal, get_price_stats
from app.modules.location_intel.service import fetch_osm_businesses
from app.modules.knowledge_base.service import get_sector_benchmark
import httpx
import os

KENYA_SECTORS_75 = [
    "Banks", "Microfinance", "Insurance", "Fintech", "Capital Markets", "SACCOs", "Retail Chains", "Wholesale",
    "FMCG Food", "FMCG Personal", "Manuf Food", "Manuf Textile", "Manuf Construction", "Manuf Auto", "Manuf Pharma",
    "Manuf Chemical", "Agri Crops", "Agri Livestock", "Agri Horticulture", "Agri Fisheries", "Agri Processing",
    "Telcos", "Media", "Advertising", "PR", "RealEstate Dev", "RealEstate Agent", "RealEstate Mgmt", "Construction",
    "Architecture", "Health Hospital", "Health Pharmacy", "Health Devices", "Edu University", "Edu School",
    "Edu EdTech", "Logistics", "E-commerce", "Hospitality Hotel", "Hospitality QSR", "Tourism", "Aviation",
    "Maritime", "Energy Electric", "Energy Oil", "Energy Renewable", "Energy Water", "Mining", "Gov National",
    "Gov County", "Gov StateCorp", "Gov Regulatory", "Public Safety", "Defense", "NGOs", "INGOs", "Donors",
    "Foundations", "Investors PEVC", "Investors Angel", "Law", "Consulting", "Accounting", "HR", "ICT",
    "Data Centers", "Digital Marketing", "Auto Dealership", "Auto Parts", "Auto Boda", "Gaming", "Entertainment",
    "Beauty", "Waste", "Environment"
]

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
CBK_URL = "https://www.centralbank.go.ke/wp-json/wp/v2/"

class MarketEngineService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)

    async def search_market(self, query: str, sector: str = None, country: str = "Kenya", county: str = None, 
                      sub_county: str = None, ward: str = None, town: str = None):
        if not sector:
            sector = await self.infer_sector_from_query(query)

        demand_level = await get_demand_signal(self.db, sector, country, county, sub_county, ward, town)
        market_size = await self.calculate_market_size(sector, country, county, sub_county, ward, town)
        price_stats = await get_price_stats(self.db, sector, None, country, county, sub_county, ward, town)
        competitors = await fetch_osm_businesses(sector, "town" if town else "ward" if ward else "subcounty" if sub_county else "county", town or ward or sub_county or county)
        competitor_count = len(competitors)
        sentiment = await get_sentiment_summary(self.db, sector, query, country, county, sub_county, ward, town)
        macro_news = await self.get_macro_news(sector)

        search_record = MarketSearch(
            query=query, sector=sector, country=country,
            county=county, sub_county=sub_county, ward=ward, town=town,
            demand_level=demand_level.get("level"), market_size_kes=market_size,
            growth_rate=demand_level.get("growth", 0),
            price_min=price_stats["min"], price_max=price_stats["max"], price_avg=price_stats["avg"],
            sentiment_summary=sentiment
        )
        self.db.add(search_record)
        self.db.commit()

        return {
            "query": query, "sector": sector, "demand_level": demand_level.get("level"),
            "market_size_kes": market_size, "growth_rate": demand_level.get("growth", 0),
            "price_range": {"min": price_stats["min"], "max": price_stats["max"], "avg": price_stats["avg"]},
            "competitor_count": competitor_count, "sentiment_summary": sentiment, "macro_news": macro_news
        }

    async def get_competitor_overview(self, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None):
        location_type = "town" if town else "ward" if ward else "subcounty" if sub_county else "county"
        location = town or ward or sub_county or county
        osm_businesses = await fetch_osm_businesses(sector, location_type, location)
        competitors = []

        for b in osm_businesses:
            comp = self.db.query(Competitor).filter(
                Competitor.sector==sector, Competitor.country==country, Competitor.county==county,
                Competitor.sub_county==sub_county, Competitor.ward==ward, Competitor.town==town,
                Competitor.lat==b["lat"], Competitor.lng==b["lon"]
            ).first()

            if not comp:
                comp = Competitor(
                    sector=sector, country=country, county=county, sub_county=sub_county, 
                    ward=ward, town=town, business_name=b.get("name", "Competitor"),
                    lat=b["lat"], lng=b["lon"], source="OSM"
                )
                self.db.add(comp)
        self.db.commit()
        return self.db.query(Competitor).filter(Competitor.sector==sector, Competitor.country==country).all()

    async def calculate_market_size(self, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None):
        benchmark = await get_sector_benchmark(sector)
        if not benchmark: return 0.0
        price_stats = await get_price_stats(self.db, sector, None, country, county, sub_county, ward, town)
        avg_price = price_stats["avg"] or benchmark.get("avg_price", 0)
        population = benchmark.get("population", 100000)
        penetration_rate = 0.05
        return round(avg_price * (population * penetration_rate) * 12, 2)

    async def get_price_stats(self, sector: str, category: str = None, country: str = "Kenya", county: str = None, sub_county: str = None, ward: str = None, town: str = None):
        from app.modules.data_layer.models import PriceTrend
        q = self.db.query(PriceTrend).filter(PriceTrend.sector==sector)
        if category: q = q.filter(PriceTrend.category==category)
        if country: q = q.filter(PriceTrend.country==country)
        if county: q = q.filter(PriceTrend.county==county)
        if sub_county: q = q.filter(PriceTrend.sub_county==sub_county)
        if ward: q = q.filter(PriceTrend.ward==ward)
        if town: q = q.filter(PriceTrend.town==town)
        prices = [p.price_kes for p in q.all()]
        if not prices: return {"min": 0, "max": 0, "avg": 0}
        return {"min": min(prices), "max": max(prices), "avg": sum(prices)/len(prices)}

    async def infer_sector_from_query(self, query: str) -> str:
        prompt = f"Map this business query to one of the 75 Kenya sectors: {KENYA_SECTORS_75}. Query: '{query}'. Return only sector name."
        ai_sector = await self.call_groq(prompt, system="You are EvidLens sector classifier. Return exact sector name only.")
        return ai_sector.strip() if ai_sector in KENYA_SECTORS_75 else "Wholesale"

    async def get_macro_news(self, sector: str):
        url = f"https://newsapi.org/v2/everything?q={sector} Kenya&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
        data = await self.call_api(url)
        articles = data.get("articles", [])[:5]
        if not articles: return []
        summary_prompt = f"Summarize these Kenya {sector} headlines for executives: {[a['title'] for a in articles]}"
        summary = await self.call_groq(summary_prompt)
        return {"articles": articles, "ai_summary": summary}

    async def get_cbk_rates(self):
        data = await self.call_api(f"{CBK_URL}rates")
        return data if data.get("status") != "no_data" else {}
