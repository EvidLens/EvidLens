import os
import httpx
import json
import asyncio
from upstash_redis import Redis
from app.core.db import SessionLocal
from sqlmodel import Session
from app.core.models import KnowledgeChunk
from datetime import datetime, timezone

UTC = timezone.utc
redis = Redis(url=os.getenv("UPSTASH_REDIS_URL"), token=os.getenv("UPSTASH_REDIS_TOKEN"))

KENYA_SECTORS = [
    "Agriculture", "Livestock & Fisheries", "Manufacturing", "Construction & Real Estate",
    "Mining & Quarrying", "Energy & Utilities", "ICT", "Telecommunications", "Banking",
    "Insurance", "Microfinance & SACCOs", "Capital Markets & Investment", "Healthcare",
    "Pharmaceuticals & Medical Supplies", "Education & Training", "Hospitality",
    "Tourism & Travel", "Transport & Logistics", "Wholesale & Retail Trade", "Automotive",
    "Media & Entertainment", "Creative & Digital Economy", "Professional Services",
    "Research & Market Intelligence", "BPO", "Government & Public Administration",
    "NGOs", "Security Services", "Environmental Services", "Water & Sanitation",
    "FinTech", "E-commerce", "Religious Organizations", "Sports & Recreation",
    "Beauty & Personal Care", "Fashion & Apparel", "Printing & Publishing", "Food & Beverage"
]

KEYWORDS = {
    "Agriculture": ["maize mill", "coffee farm", "horticulture"],
    "Livestock & Fisheries": ["dairy farm", "poultry", "fish farming"],
    "Manufacturing": ["factory", "packaging", "textile"],
    "Construction & Real Estate": ["hardware", "contractor", "rental"],
    "Mining & Quarrying": ["quarry", "sand", "cement"],
    "Energy & Utilities": ["solar", "gas", "generator"],
    "ICT": ["software", "cyber cafe", "app development"],
    "Telecommunications": ["safaricom", "airtel", "internet"],
    "Banking": ["bank", "loan", "credit"],
    "Insurance": ["insurance", "cover", "claims"],
    "Microfinance & SACCOs": ["sacco", "microloan", "chama"],
    "Capital Markets & Investment": ["stocks", "bonds", "investment"],
    "Healthcare": ["clinic", "hospital", "doctor"],
    "Pharmaceuticals & Medical Supplies": ["pharmacy", "drugs", "medical"],
    "Education & Training": ["school", "tutoring", "edtech"],
    "Hospitality": ["hotel", "restaurant", "airbnb"],
    "Tourism & Travel": ["safari", "tour", "travel agency"],
    "Transport & Logistics": ["boda boda", "logistics", "matatu"],
    "Wholesale & Retail Trade": ["supermarket", "retail shop", "wholesale"],
    "Automotive": ["garage", "car wash", "spare parts"],
    "Media & Entertainment": ["radio", "tv", "content"],
    "Creative & Digital Economy": ["design", "video", "freelance"],
    "Professional Services": ["lawyer", "consultant", "accountant"],
    "Research & Market Intelligence": ["survey", "research", "data"],
    "BPO": ["call center", "bpo", "outsourcing"],
    "Government & Public Administration": ["tender", "government", "public"],
    "NGOs": ["ngo", "donor", "project"],
    "Security Services": ["security", "guard", "cctv"],
    "Environmental Services": ["waste", "recycling", "cleaning"],
    "Water & Sanitation": ["water", "borehole", "sanitation"],
    "FinTech": ["m-pesa agent", "fintech", "wallet"],
    "E-commerce": ["ecommerce", "online shop", "delivery"],
    "Religious Organizations": ["church", "mosque", "donation"],
    "Sports & Recreation": ["gym", "sports", "recreation"],
    "Beauty & Personal Care": ["salon", "barber", "spa"],
    "Fashion & Apparel": ["boutique", "tailor", "clothes"],
    "Printing & Publishing": ["printing", "publishing", "branding"],
    "Food & Beverage": ["restaurant", "food truck", "bakery"]
}

async def save_chunk(db: Session, sector: str, text: str, source: str, chunk_type: str):
    chunk = KnowledgeChunk(
        sector=sector,
        chunk_text=text[:2000], # cap it
        chunk_type=chunk_type,
        source=source,
        chunk_metadata={"loaded_at": datetime.now(UTC).isoformat()}
    )
    db.add(chunk)

async def load_knbs_to_rag():
    db = SessionLocal()
    for sector in KENYA_SECTORS:
        # DUMMY KNBS data until you build scraper
        data = {"sector": sector, "source": "knbs", "note": "Replace with real KNBS API", "timestamp": datetime.now(UTC).isoformat()}
        await save_chunk(db, sector, json.dumps(data), "KNBS", "macro_stat")
        redis.set(f"rag:knbs:{sector}", json.dumps(data))
    db.commit()
    db.close()

async def load_reddit_to_rag():
    db = SessionLocal()
    async with httpx.AsyncClient(timeout=15) as client:
        for sector in KENYA_SECTORS:
            for kw in KEYWORDS.get(sector, [sector.lower()]):
                try:
                    res = await client.get(
                        f"https://www.reddit.com/search.json?q={kw}+Kenya",
                        headers={"User-Agent": os.getenv("REDDIT_USER_AGENT", "EvidLensBot/1.0")}
                    )
                    posts = res.json().get("data", {}).get("children", [])[:10]
                    texts = [p["data"]["title"] + " " + p["data"].get("selftext", "") for p in posts] # FIXED

                    full_text = "\n".join(texts)
                    await save_chunk(db, sector, full_text, f"Reddit:{kw}", "social_sentiment")
                    redis.set(f"rag:reddit:{sector}:{kw}", json.dumps(texts))
                    await asyncio.sleep(0.5) # don't rate limit
                except Exception as e:
                    print(f"Reddit error for {kw}: {e}")
    db.commit()
    db.close()

async def load_fmcg_to_rag():
    # You need to create this json file and upload to /data
    db = SessionLocal()
    try:
        with open("data/fmcg_catalog.json", "r") as f:
            catalog = json.load(f)
        await save_chunk(db, "Wholesale & Retail Trade", json.dumps(catalog), "FMCG_Catalog", "product_catalog")
        redis.set("rag:fmcg:catalog", json.dumps({"status": "seeded", "count": len(catalog)}))
    except FileNotFoundError:
        print("data/fmcg_catalog.json not found. Skipping.")
    db.commit()
    db.close()

async def run_rag_load():
    await asyncio.gather(
        load_knbs_to_rag(),
        load_reddit_to_rag(),
        load_fmcg_to_rag()
    )
    redis.set("rag:last_updated", datetime.now(UTC).isoformat())
    redis.set("rag:sector_count", len(KENYA_SECTORS))
    print(f"RAG Load Complete: {len(KENYA_SECTORS)} sectors saved to Redis + DB")
