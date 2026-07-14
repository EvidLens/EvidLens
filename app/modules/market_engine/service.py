from sqlalchemy.orm import Session
from sqlalchemy import func
from.models import MarketSearch, Competitor
from app.modules.consumer_voice.service import get_sentiment_summary
from app.modules.data_layer.service import get_demand_signal, get_price_stats
from app.modules.location_intel.service import fetch_osm_businesses
from app.modules.knowledge_base.service import get_sector_benchmark

KENYA_SECTORS_75 = [
    "Agriculture", "Livestock", "Fisheries", "Forestry", "Manufacturing", "Construction", "Real Estate",
    "Mining", "Quarrying", "Oil & Gas", "Energy", "Utilities", "Water Supply", "Waste Management", "Sanitation",
    "ICT", "Telecommunications", "Software", "Data Services", "Banking", "Insurance", "Microfinance", "SACCOs",
    "Capital Markets", "Investment", "Pension", "Healthcare", "Pharmaceuticals", "Medical Devices", "Education",
    "Vocational Training", "Hospitality", "Tourism", "Travel", "Transport", "Logistics", "Warehousing", 
    "Wholesale Trade", "Retail Trade", "E-commerce", "Automotive", "Media", "Broadcasting", "Publishing", 
    "Advertising", "Creative Arts", "Digital Economy", "Professional Services", "Legal Services", "Accounting",
    "Consulting", "Research", "Market Intelligence", "BPO", "Government", "Public Administration", "NGOs",
    "Security", "Environmental Services", "FinTech", "Sports", "Recreation", "Beauty", "Personal Care", 
    "Fashion", "Textiles", "Printing", "Food Processing", "Beverages", "Religious Organizations", "Events",
    "Rental & Leasing", "Repair & Maintenance"
]

def search_market(db: Session, query: str, sector: str = None, country: str = "Kenya", county: str = None, sub_county: str = None, ward: str = None, town: str = None):
    if not sector:
        sector = infer_sector_from_query(query)

    demand_level = get_demand_signal(db, sector, country, county, sub_county, ward, town)
    market_size = calculate_market_size(db, sector, country, county, sub_county, ward, town)
    price_stats = get_price_stats(db, sector, None, country, county, sub_county, ward, town)
    competitors = fetch_osm_businesses(sector, "town" if town else "ward" if ward else "subcounty" if sub_county else "county", town or ward or sub_county or county)
    competitor_count = len(competitors)
    sentiment = get_sentiment_summary(db, sector, query, country, county, sub_county, ward, town)

    search_record = MarketSearch(
        query=query, sector=sector, country=country,
        county=county, sub_county=sub_county, ward=ward, town=town,
        demand_level=demand_level["level"], market_size_kes=market_size,
        growth_rate=demand_level.get("growth", 0),
        price_min=price_stats["min"], price_max=price_stats["max"], price_avg=price_stats["avg"],
        sentiment_summary=sentiment
    )
    db.add(search_record)
    db.commit()

    return {
        "query": query, "sector": sector, "demand_level": demand_level["level"],
        "market_size_kes": market_size, "growth_rate": demand_level.get("growth", 0),
        "price_range": {"min": price_stats["min"], "max": price_stats["max"], "avg": price_stats["avg"]},
        "competitor_count": competitor_count, "sentiment_summary": sentiment
    }

def get_competitor_overview(db: Session, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None):
    location_type = "town" if town else "ward" if ward else "subcounty" if sub_county else "county"
    location = town or ward or sub_county or county
    osm_businesses = fetch_osm_businesses(sector, location_type, location)
    competitors = []

    for b in osm_businesses:
        comp = db.query(Competitor).filter(
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
            db.add(comp)
    db.commit()
    return db.query(Competitor).filter(Competitor.sector==sector, Competitor.country==country).all()

def calculate_market_size(db: Session, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None):
    benchmark = get_sector_benchmark(sector)
    if not benchmark: return 0.0
    price_stats = get_price_stats(db, sector, None, country, county, sub_county, ward, town)
    avg_price = price_stats["avg"] or benchmark.get("avg_price", 0)
    population = benchmark.get("population", 100000)
    penetration_rate = 0.05
    return round(avg_price * (population * penetration_rate) * 12, 2)

def get_price_stats(db: Session, sector: str, category: str = None, country: str = "Kenya", county: str = None, sub_county: str = None, ward: str = None, town: str = None):
    from app.modules.data_layer.models import PriceTrend
    q = db.query(PriceTrend).filter(PriceTrend.sector==sector)
    if category: q = q.filter(PriceTrend.category==category)
    if country: q = q.filter(PriceTrend.country==country)
    if county: q = q.filter(PriceTrend.county==county)
    if sub_county: q = q.filter(PriceTrend.sub_county==sub_county)
    if ward: q = q.filter(PriceTrend.ward==ward)
    if town: q = q.filter(PriceTrend.town==town)
    prices = [p.price_kes for p in q.all()]
    if not prices: return {"min": 0, "max": 0, "avg": 0}
    return {"min": min(prices), "max": max(prices), "avg": sum(prices)/len(prices)}

def infer_sector_from_query(query: str) -> str:
    query = query.lower()
    mapping = {
        "agriculture": ["farming", "crop", "agriculture"],
        "livestock": ["livestock", "animal husbandry"],
        "fisheries": ["fisheries", "aquaculture"],
        "manufacturing": ["manufacturing", "factory", "production"],
        "construction": ["construction", "building", "contractor"],
        "real estate": ["real estate", "property", "housing"],
        "healthcare": ["healthcare", "clinic", "hospital"],
        "education": ["education", "school", "university"],
        "ict": ["ict", "software", "tech"],
        "banking": ["banking", "financial services"],
        "transport": ["transport", "logistics"],
        "retail trade": ["retail", "trade", "commerce"],
        "hospitality": ["hospitality", "hotel", "accommodation"],
        "tourism": ["tourism", "travel"],
        "fintech": ["fintech", "digital finance"],
        "e-commerce": ["e-commerce", "online"],
        "energy": ["energy", "power"],
        "food processing": ["food", "beverage"]
    }
    for sector, keywords in mapping.items():
        if any(k in query for k in keywords):
            return sector.title()
    return "Wholesale Trade"
