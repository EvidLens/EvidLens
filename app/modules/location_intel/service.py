import os
import requests
from sqlalchemy.orm import Session
from sqlalchemy import func
from.models import LocationComparison, OpportunityHeatmap, PriceArbitrage, LocationGeo
from app.modules.data_layer.models import PriceTrend, DemandSignal
from app.modules.consumer_voice.models import SentimentSummary

LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def seed_geo_data(db: Session):
    queries = {
        "county": '[out:json]; area["ISO3166-2"="KE"]["admin_level"="2"]->.ke; relation["admin_level"="4"](area.ke); out tags;',
        "subcounty": '[out:json]; area["ISO3166-2"="KE"]["admin_level"="2"]->.ke; relation["admin_level"="6"](area.ke); out tags;',
        "ward": '[out:json]; area["ISO3166-2"="KE"]["admin_level"="2"]->.ke; relation["admin_level"="9"](area.ke); out tags;',
        "town": '[out:json]; area["ISO3166-2"="KE"]["admin_level"="2"]->.ke; node["place"~"town|city"](area.ke); out 2000;'
    }
    for level, query in queries.items():
        try:
            r = requests.post(OVERPASS_URL, data=query, timeout=60).json()
            for el in r.get("elements", []):
                name = el.get("tags", {}).get("name")
                parent = el.get("tags", {}).get("is_in:county")
                if name:
                    geo = LocationGeo(level=level, name=name, parent=parent)
                    db.merge(geo)
        except:
            pass
    db.commit()

def get_location_comparison(db: Session, sector: str, location_a: str, location_b: str, location_type: str):
    price_a = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector, getattr(PriceTrend, location_type)==location_a).scalar() or 0
    price_b = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector, getattr(PriceTrend, location_type)==location_b).scalar() or 0
    demand_a = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector, getattr(DemandSignal, location_type)==location_a).scalar() or 0
    demand_b = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector, getattr(DemandSignal, location_type)==location_b).scalar() or 0
    sentiment_a = db.query(SentimentSummary.avg_sentiment_score).filter(SentimentSummary.sector==sector, getattr(SentimentSummary, location_type)==location_a).scalar() or 0
    sentiment_b = db.query(SentimentSummary.avg_sentiment_score).filter(SentimentSummary.sector==sector, getattr(SentimentSummary, location_type)==location_b).scalar() or 0
    businesses_a = len(fetch_osm_businesses(sector, location_type, location_a))
    businesses_b = len(fetch_osm_businesses(sector, location_type, location_b))
    score_a = (demand_a * 0.4) + (sentiment_a * 0.3) - (businesses_a * 0.1) - (price_a * 0.0001)
    score_b = (demand_b * 0.4) + (sentiment_b * 0.3) - (businesses_b * 0.1) - (price_b * 0.0001)
    opportunity_gap = score_a - score_b
    recommendation = location_a if score_a > score_b else location_b
    comparison = LocationComparison(
        sector=sector,
        location_type=location_type,
        location_a=location_a,
        location_b=location_b,
        comparison_data={
            "score_a": score_a,
            "score_b": score_b,
            "business_density_a": businesses_a,
            "business_density_b": businesses_b,
            "avg_price_a": price_a,
            "avg_price_b": price_b,
            "demand_a": demand_a,
            "demand_b": demand_b,
            "sentiment_a": sentiment_a,
            "sentiment_b": sentiment_b,
            "opportunity_gap": opportunity_gap,
            "recommendation": recommendation
        }
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison

def generate_heatmap(db: Session, sector: str, location_type: str, location: str = None):
    heatmap_data = []
    q = db.query(LocationGeo).filter(LocationGeo.level==location_type)
    if location:
        q = q.filter(LocationGeo.parent==location)
    locations = q.all()
    for loc in locations:
        demand = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector, getattr(DemandSignal, location_type)==loc.name).scalar() or 0
        sentiment = db.query(SentimentSummary.avg_sentiment_score).filter(SentimentSummary.sector==sector, getattr(SentimentSummary, location_type)==loc.name).scalar() or 0
        businesses = len(fetch_osm_businesses(sector, location_type, loc.name))
        opportunity_score = min(100, max(0, (demand * 10) + (sentiment * 20) - (businesses * 2)))
        lat, lng = get_coords(loc.name, location_type)
        heatmap = OpportunityHeatmap(
            sector=sector,
            country="Kenya",
            county=loc.parent if location_type!="county" else loc.name,
            sub_county=loc.parent if location_type=="ward" else None,
            ward=loc.parent if location_type=="town" else None,
            town=loc.name if location_type=="town" else None,
            opportunity_score=opportunity_score,
            lat=lat,
            lng=lng,
            factors={"demand": demand, "sentiment": sentiment, "competition": businesses}
        )
        db.merge(heatmap)
        heatmap_data.append(heatmap)
    db.commit()
    return heatmap_data

def fetch_osm_businesses(sector: str, location_type: str, location: str):
    osm_tags = {
        "Retail Trade": "shop",
        "Food & Beverage": "amenity=restaurant",
        "Healthcare": "amenity=clinic",
        "Banking": "amenity=bank",
        "Hospitality": "tourism=hotel"
    }
    tag = osm_tags.get(sector, "shop")
    admin_map = {"county": 4, "subcounty": 6, "ward": 9, "town": 8}
    admin_level = admin_map.get(location_type, 4)
    query = f'[out:json]; area["name"="{location}"]["admin_level"="{admin_level}"]->.a; node[{tag}](area.a); out 100;'
    try:
        response = requests.post(OVERPASS_URL, data=query, timeout=15).json()
        return [{"lat": e["lat"], "lon": e["lon"], "id": e["id"]} for e in response.get("elements", [])]
    except:
        return []

def get_coords(name: str, location_type: str):
    try:
        url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_API_KEY}&q={name},Kenya&format=json"
        r = requests.get(url, timeout=5).json()
        if r:
            return float(r[0]["lat"]), float(r[0]["lon"])
    except:
        pass
    return None, None

def calculate_price_arbitrage(db: Session, product: str, location_type: str):
    prices = db.query(PriceTrend).filter(PriceTrend.product_name==product).all()
    results = []
    for p1 in prices:
        for p2 in prices:
            loc1 = getattr(p1, location_type)
            loc2 = getattr(p2, location_type)
            if loc1!= loc2:
                gap = abs(p1.price_kes - p2.price_kes)
                margin = (gap / min(p1.price_kes, p2.price_kes)) * 100 if min(p1.price_kes, p2.price_kes) > 0 else 0
                if gap > 50:
                    arb = PriceArbitrage(
                        product=product,
                        location_type=location_type,
                        county_from=p1.county if p1.price_kes < p2.price_kes else p2.county,
                        county_to=p2.county if p1.price_kes < p2.price_kes else p1.county,
                        sub_county_from=getattr(p1, "sub_county", None) if p1.price_kes < p2.price_kes else getattr(p2, "sub_county", None),
                        sub_county_to=getattr(p2, "sub_county", None) if p1.price_kes < p2.price_kes else getattr(p1, "sub_county", None),
                        town_from=getattr(p1, "town", None) if p1.price_kes < p2.price_kes else getattr(p2, "town", None),
                        town_to=getattr(p2, "town", None) if p1.price_kes < p2.price_kes else getattr(p1, "town", None),
                        price_gap_kes=gap,
                        margin_percent=margin
                    )
                    db.merge(arb)
                    results.append(arb)
    db.commit()
    return results[:20]
