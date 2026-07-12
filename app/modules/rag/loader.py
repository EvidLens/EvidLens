import os, httpx, json
from upstash_redis import Redis
from app.modules.db import SessionLocal
from app.modules.data_layer.service import fetch_demand_signals, seed_fmcg_catalog
import asyncio

redis = Redis(url=os.getenv("UPSTASH_REDIS_URL"), token=os.getenv("UPSTASH_REDIS_TOKEN"))

SECTORS = [
    "Agriculture", "Retail", "Health", "Education", "Technology", 
    "Finance", "Manufacturing", "Real Estate", "Transport", "Hospitality",
    "Food & Beverage", "Beauty", "Construction", "Energy"
]

KEYWORDS = {
    "Agriculture": ["maize mill", "dairy farm", "poultry"],
    "Retail": ["supermarket", "retail shop", "wholesale"],
    "Health": ["clinic", "pharmacy", "hospital"],
    "Education": ["school", "tutoring", "edtech"],
    "Technology": ["software", "cyber cafe", "app development"],
    "Finance": ["m-pesa agent", "sacco", "fintech"],
    "Manufacturing": ["factory", "soap making", "packaging"],
    "Real Estate": ["rental", "property", "construction"],
    "Transport": ["boda boda", "logistics", "matatu"],
    "Hospitality": ["hotel", "restaurant", "airbnb"],
    "Food & Beverage": ["restaurant", "food truck", "bakery"],
    "Beauty": ["salon", "barber", "spa"],
    "Construction": ["hardware", "contractor", "cement"],
    "Energy": ["solar", "gas", "generator"]
}

async def load_knbs_to_rag():
    db = SessionLocal()
    for sector in SECTORS:
        fetch_demand_signals(db, sector)
        data = {"sector": sector, "source": "knbs", "timestamp": "2026-04-29"}
        redis.set(f"rag:knbs:{sector}", json.dumps(data))
    db.close()

async def load_reddit_to_rag():
    async with httpx.AsyncClient() as client:
        for sector in SECTORS:
            for kw in KEYWORDS[sector]:
                res = await client.get(
                    f"https://www.reddit.com/search.json?q={kw}+Kenya", 
                    headers={"User-Agent": os.getenv("
