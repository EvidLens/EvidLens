from sqlalchemy.orm import Session
from.models import MarketSearch, Competitor
from app.modules.consumer_voice.service import get_sentiment_summary
from app.modules.data_layer.service import get_demand_signal, get_price_stats
from app.modules.location_intel.service import fetch_osm_businesses
from app.modules.knowledge_base.service import get_sector_benchmark

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

def search_market(db: Session, query: str, sector: str = None, county: str = None):
    if not sector:
        sector = infer_sector_from_query(query)

    demand_level = get_demand_signal(db, sector, county)
    market_size = calculate_market_size(db, sector, county)
    price_stats = get_price_stats(db, sector, query, county)
    competitors = fetch_osm_businesses(sector, county) if county else []
    competitor_count = len(competitors)
    sentiment = get_sentiment_summary(db, sector, query, county)

    search_record = MarketSearch(
        query=query,
        sector=sector,
        county=county,
        demand_level=demand_level["level"],
        market_size_kes=market_size,
        price_min=price_stats["min"],
        price_max=price_stats["max"],
        price_avg=price_stats["avg"],
        sentiment_summary=sentiment
    )
    db.add(search_record)
    db.commit()

    return {
        "query": query,
        "sector": sector,
        "county": county,
        "demand_level": demand_level["level"],
        "market_size_kes": market_size,
        "growth_rate": demand_level.get("growth", 0),
        "price_range": {
            "min_kes": price_stats["min"],
            "max_kes": price_stats["max"],
            "avg_kes": price_stats["avg"]
        },
        "competitor_count": competitor_count,
        "sentiment_summary": sentiment
    }

def get_competitor_overview(db: Session, sector: str, county: str):
    osm_businesses = fetch_osm_businesses(sector, county)
    competitors = []

    for b in osm_businesses:
        comp = db.query(Competitor).filter(
            Competitor.sector==sector,
            Competitor.county==county,
            Competitor.lat==b["lat"],
            Competitor.lng==b["lon"]
        ).first()

        if not comp:
            comp = Competitor(
                sector=sector,
                county=county,
                business_name=b.get("name", f"Business {b['id']}"),
                lat=b["lat"],
                lng=b["lon"],
                source="OSM"
            )
            db.add(comp)
            db.commit()
            db.refresh(comp)
        competitors.append(comp)

    return competitors

def calculate_market_size(db: Session, sector: str, county: str = None):
    benchmark = get_sector_benchmark(sector)
    if not benchmark:
        return 0.0

    price_stats = get_price_stats(db, sector, None, county)
    avg_price = price_stats["avg"] or benchmark.get("avg_price", 0)
    population = benchmark.get("county_population", 100000) if county else benchmark.get("national_population", 50000000)
    penetration_rate = 0.05

    annual_market = avg_price * (population * penetration_rate) * 12
    return round(annual_market, 2)

def infer_sector_from_query(query: str) -> str:
    query = query.lower()
    if any(k in query for k in ["maize", "wheat", "tea", "coffee", "farming"]):
        return "Agriculture"
    if any(k in query for k in ["milk", "cow", "chicken", "fish"]):
        return "Livestock & Fisheries"
    if any(k in query for k in ["factory", "manufacturing", "production"]):
        return "Manufacturing"
    if any(k in query for k in ["construction", "house", "building", "land"]):
        return "Construction & Real Estate"
    if any(k in query for k in ["mining", "quarry"]):
        return "Mining & Quarrying"
    if any(k in query for k in ["energy", "electricity", "solar"]):
        return "Energy & Utilities"
    if any(k in query for k in ["software", "app", "website", "developer"]):
        return "ICT"
    if any(k in query for k in ["internet", "safaricom", "telco"]):
        return "Telecommunications"
    if any(k in query for k in ["bank", "loan"]):
        return "Banking"
    if any(k in query for k in ["mpesa", "fintech"]):
        return "FinTech"
    if any(k in query for k in ["insurance", "policy"]):
        return "Insurance"
    if any(k in query for k in ["sacco", "microfinance"]):
        return "Microfinance & SACCOs"
    if any(k in query for k in ["investment", "stocks"]):
        return "Capital Markets & Investment"
    if any(k in query for k in ["clinic", "hospital", "doctor"]):
        return "Healthcare"
    if any(k in query for k in ["pharmacy", "drugs"]):
        return "Pharmaceuticals & Medical Supplies"
    if any(k in query for k in ["school", "university", "training"]):
        return "Education & Training"
    if any(k in query for k in ["hotel", "lodging", "bnb"]):
        return "Hospitality"
    if any(k in query for k in ["tour", "safari", "travel"]):
        return "Tourism & Travel"
    if any(k in query for k in ["transport", "matatu", "logistics"]):
        return "Transport & Logistics"
    if any(k in query for k in ["shop", "retail", "store"]):
        return "Wholesale & Retail Trade"
    if any(k in query for k in ["car", "garage", "auto"]):
        return "Automotive"
    if any(k in query for k in ["media", "tv", "radio"]):
        return "Media & Entertainment"
    if any(k in query for k in ["creative", "content", "influencer"]):
        return "Creative & Digital Economy"
    if any(k in query for k in ["lawyer", "consultant", "audit"]):
        return "Professional Services"
    if any(k in query for k in ["research", "survey"]):
        return "Research & Market Intelligence"
    if any(k in query for k in ["bpo", "call center"]):
        return "BPO"
    if any(k in query for k in ["government", "county"]):
        return "Government & Public Administration"
    if any(k in query for k in ["ngo", "charity"]):
        return "NGOs"
    if any(k in query for k in ["security", "guard"]):
        return "Security Services"
    if any(k in query for k in ["environment", "waste"]):
        return "Environmental Services"
    if any(k in query for k in ["sanitation", "water"]):
        return "Water & Sanitation"
    if any(k in query for k in ["ecommerce", "jumia", "online shop"]):
        return "E-commerce"
    if any(k in query for k in ["church", "mosque"]):
        return "Religious Organizations"
    if any(k in query for k in ["sports", "gym"]):
        return "Sports & Recreation"
    if any(k in query for k in ["beauty", "salon", "barber"]):
        return "Beauty & Personal Care"
    if any(k in query for k in ["fashion", "clothes", "boutique"]):
        return "Fashion & Apparel"
    if any(k in query for k in ["printing", "publisher"]):
        return "Printing & Publishing"
    if any(k in query for k in ["restaurant", "food", "cafe"]):
        return "Food & Beverage"
    return "Wholesale & Retail Trade"
