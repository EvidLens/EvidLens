from sqlalchemy.orm import Session
from sqlalchemy import func
from.models import MarketSearch, Competitor, MarketMetric
from app.modules.consumer_voice.service import get_sentiment_summary
from app.modules.data_layer.service import get_demand_signal, get_price_stats
from app.modules.location_intel.service import fetch_osm_businesses
from app.modules.knowledge_base.service import get_sector_benchmark

def search_market(db: Session, query: str, sector: str = None, county: str = None):
    """Main aggregation function. Powers /search endpoint"""
    
    # 1. Auto-detect sector from query if not provided
    if not sector:
        sector = infer_sector_from_query(query)
    
    # 2. Lane 3: Demand + Market Size
    demand_level = get_demand_signal(db, sector, county)
    market_size = calculate_market_size(db, sector, county)
    
    # 3. Lane 3: Pricing
    price_stats = get_price_stats(db, sector, query, county)
    
    # 4. Lane 6: Competitor count
    competitors = fetch_osm_businesses(sector, county) if county else []
    competitor_count = len(competitors)
    
    # 5. Lane 2: Sentiment
    sentiment = get_sentiment_summary(db, sector, query, county)
    
    # 6. Save search for trending
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
    """Pull competitors from OSM + merge with ratings from Lane 2"""
    osm_businesses = fetch_osm_businesses(sector, county)
    competitors = []
    
    for b in osm_businesses:
        # Check if we have reviews for this business
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
                business_name=f"Business {b['id']}",
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
    """Estimate market size using KNBS + price * demand. Lane 3 + 7"""
    benchmark = get_sector_benchmark(sector)
    if not benchmark:
        return 0.0
    
    # Simple formula: avg_price * monthly_transactions * 12
    price_stats = get_price_stats(db, sector, None, county)
    avg_price = price_stats["avg"] or benchmark["avg_price"]
    
    # Get population/demand proxy from KNBS data in knowledge_base
    population = benchmark.get("county_population", 100000) if county else benchmark.get("national_population", 50000000)
    penetration_rate = 0.05 # 5% default
    
    annual_market = avg_price * (population * penetration_rate) * 12
    return round(annual_market, 2)

def infer_sector_from_query(query: str) -> str:
    """Basic NLP to map query to 1 of 36 sectors"""
    query = query.lower()
    sector_map = {
        "maize": "Agriculture", "milk": "Agriculture", "farming": "Agriculture",
        "shop": "Wholesale & Retail Trade", "retail": "Wholesale & Retail Trade",
        "restaurant": "Food & Beverage", "hotel": "Hospitality",
        "clinic": "Healthcare", "pharmacy": "Healthcare",
        "software": "ICT", "app": "ICT", "internet": "ICT",
        "bank": "Banking", "loan": "Banking", "sacco": "Banking"
    }
    for keyword, sector in sector_map.items():
        if keyword in query:
            return sector
    return "Wholesale & Retail Trade" # default
