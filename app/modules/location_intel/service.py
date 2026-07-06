import os
import requests
from sqlalchemy.orm import Session
from sqlalchemy import func
from.models import LocationComparison, OpportunityHeatmap, PriceArbitrage, KENYA_COUNTIES
from app.modules.data_layer.models import PriceTrend, DemandSignal
from app.modules.consumer_voice.models import SentimentSummary

LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def get_county_comparison(db: Session, sector: str, county_a: str, county_b: str):
    """Compare 2 counties for a sector. Returns opportunity gap + recommendation"""

    # Pull metrics from other lanes
    price_a = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector, PriceTrend.county==county_a).scalar() or 0
    price_b = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector, PriceTrend.county==county_b).scalar() or 0

    demand_a = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector, DemandSignal.county==county_a).scalar() or 0
    demand_b = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector, DemandSignal.county==county_b).scalar() or 0

    sentiment_a = db.query(SentimentSummary.avg_sentiment_score).filter(SentimentSummary.sector==sector, SentimentSummary.county==county_a).scalar() or 0
    sentiment_b = db.query(SentimentSummary.avg_sentiment_score).filter(SentimentSummary.sector==sector, SentimentSummary.county==county_b).scalar() or 0

    businesses_a = len(fetch_osm_businesses(sector, county_a))
    businesses_b = len(fetch_osm_businesses(sector, county_b))

    # Simple scoring: Higher demand + sentiment - competition = better
    score_a = (demand_a * 0.4) + (sentiment_a * 0.3) - (businesses_a * 0.1) - (price_a * 0.0001)
    score_b = (demand_b * 0.4) + (sentiment_b * 0.3) - (businesses_b * 0.1) - (price_b * 0.0001)

    opportunity_gap = score_a - score_b
    recommendation = county_a if score_a > score_b else county_b

    comparison = LocationComparison(
        sector=sector,
        location_a=county_a,
        location_b=county_b,
        business_density_a=businesses_a,
        business_density_b=businesses_b,
        avg_price_a=price_a,
        avg_price_b=price_b,
        demand_score_a=demand_a,
        demand_score_b=demand_b,
        sentiment_score_a=sentiment_a,
        sentiment_score_b=sentiment_b,
        opportunity_gap=opportunity_gap,
        recommendation=f"Better opportunity in {recommendation}"
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison

def generate_heatmap(db: Session, sector: str, urban_rural: str = None):
    """Generate opportunity score 0-100 for all 47 counties. Powers County Heatmap"""
    heatmap_data = []

    for county in KENYA_COUNTIES:
        demand = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector, DemandSignal.county==county).scalar() or 0
        sentiment = db.query(SentimentSummary.avg_sentiment_score).filter(SentimentSummary.sector==sector, SentimentSummary.county==county).scalar() or 0
        businesses = len(fetch_osm_businesses(sector, county))

        # Normalize to 0-100
        opportunity_score = min(100, max(0, (demand * 10) + (sentiment * 20) - (businesses * 2)))

        # Get lat/lng from LocationIQ
        lat, lng = get_county_coords(county)

        heatmap = OpportunityHeatmap(
            sector=sector,
            county=county,
            opportunity_score=opportunity_score,
            lat=lat,
            lng=lng,
            urban_rural=urban_rural,
            factors={"demand": demand, "sentiment": sentiment, "competition": businesses}
        )
        db.merge(heatmap)
        heatmap_data.append(heatmap)

    db.commit()
    return heatmap_data

def fetch_osm_businesses(sector: str, county: str):
    """Pull competitor locations from OSM Overpass API. Free"""
    osm_tags = {
        "Retail Trade": "shop",
        "Food & Beverage": "amenity=restaurant",
        "Healthcare": "amenity=clinic",
        "Banking": "amenity=bank",
        "Hospitality": "tourism=hotel"
    }
    tag = osm_tags.get(sector, "shop")

    query = f"""
    [out:json];
    area["name"="{county}"]["admin_level"="4"]->.searchArea;
    node[{tag}](area.searchArea);
    out 50;
    """
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=10)
        data = response.json()
        return [{"lat": e["lat"], "lon": e["lon"], "id": e["id"]} for e in data.get("elements", [])]
    except:
        return []

def get_county_coords(county: str):
    """Get lat/lng from LocationIQ. 10k/day free"""
    try:
        url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_API_KEY}&q={county},Kenya&format=json"
        r = requests.get(url, timeout=5).json()
        if r:
            return float(r[0]["lat"]), float(r[0]["lon"])
    except:
        pass
    return None, None

def calculate_price_arbitrage(db: Session, product: str):
    """Find price gaps between counties. Powers Price Arbitrage Maps"""
    prices = db.query(PriceTrend).filter(PriceTrend.product_name==product).all()
    results = []

    for p1 in prices:
        for p2 in prices:
            if p1.county!= p2.county:
                gap = abs(p1.price_kes - p2.price_kes)
                margin = (gap / min(p1.price_kes, p2.price_kes)) * 100 if min(p1.price_kes, p2.price_kes) > 0 else 0

                if gap > 50: # Only show meaningful gaps
                    arb = PriceArbitrage(
                        product_name=product,
                        category=p1.category,
                        county_from=p1.county if p1.price_kes < p2.price_kes else p2.county,
                        county_to=p2.county if p1.price_kes < p2.price_kes else p1.county,
                        price_from=min(p1.price_kes, p2.price_kes),
                        price_to=max(p1.price_kes, p2.price_kes),
                        price_gap_kes=gap,
                        margin_percent=margin
                    )
                    db.merge(arb)
                    results.append(arb)
    db.commit()
    return results[:20] # Top 20 opportunities
