import os
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from.models import PriceTrend, DemandSignal, LocationMetric, FMCGCatalog, DataSource

LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_API_KEY")
KNBS_API_URL = "https://api.knbs.or.ke/v1"

def fetch_price_trends(db: Session):
    """Weekly scrape Jumia + Naivas for KE prices. Powers Price Arbitrage Maps"""
    count = 0
    sources = [
        {"name": "jumia", "url": "https://www.jumia.co.ke/groceries/"},
        {"name": "naivas", "url": "https://www.naivas.online/category/food-cupboard"}
    ]

    for src in sources:
        try:
            res = requests.get(src["url"], headers={"User-Agent": "EvidLensBot/1.0"}, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")

            # Jumia example selector - adjust as needed
            products = soup.select(".prd")[:20]
            for p in products:
                name = p.select_one(".name").text.strip() if p.select_one(".name") else "Unknown"
                price_text = p.select_one(".prc").text.replace("KSh", "").replace(",", "").strip()
                price = float(price_text) if price_text else 0.0

                prev = db.query(PriceTrend).filter(PriceTrend.product_name == name).order_by(PriceTrend.scraped_at.desc()).first()
                change = ((price - prev.price_kes) / prev.price_kes * 100) if prev and prev.price_kes else 0.0

                trend = PriceTrend(
                    sector="Food & Beverage",
                    fmcg_category="Food & Staples",
                    product_name=name,
                    price_kes=price,
                    previous_price_kes=prev.price_kes if prev else None,
                    price_change_percent=round(change, 2),
                    source=DataSource[src["name"]],
                    county="Nairobi"
                )
                db.add(trend)
                count += 1
        except Exception as e:
            print(f"Scrape error {src['name']}: {e}")

    db.commit()
    return count

def fetch_demand_signals(db: Session, sector: str) -> int:
    """Pull demand from KNBS API + Google Trends proxy"""
    count = 0
    try:
        # KNBS API call
        res = requests.get(f"{KNBS_API_URL}/data?sector={sector}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            for item in data.get("results", [])[:10]:
                signal = DemandSignal(
                    sector=sector,
                    county=item.get("county"),
                    signal_type="knbs_index",
                    signal_value=float(item.get("value", 0)),
                    signal_source=DataSource.knbs,
                    period=item.get("period", datetime.now().strftime("%Y-%m"))
                )
                db.add(signal)
                count += 1
    except:
        pass

    # Google Trends mock - replace with pytrends in prod
    signal = DemandSignal(
        sector=sector,
        signal_type="google_trends",
        signal_value=65.0,
        signal_source=DataSource.google_trends,
        period=datetime.now().strftime("%Y-%m")
    )
    db.add(signal)
    count += 1
    db.commit()
    return count

def fetch_location_analytics(db: Session, sector: str) -> int:
    """Use OSM Overpass + LocationIQ for County x Sector business density"""
    count = 0
    counties = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]

    for county in counties:
        try:
            # LocationIQ forward geocode
            url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_KEY}&q={county}+Kenya&format=json"
            res = requests.get(url, timeout=5)
            geo = res.json()[0] if res.status_code == 200 else {}

            # OSM Overpass - count businesses in sector
            overpass_query = f"""
            [out:json];
            area["name"="{county}"]->.searchArea;
            node["shop"](area.searchArea);
            out count;
            """
            osm_res = requests.post("https://overpass-api.de/api/interpreter", data=overpass_query)
            business_count = osm_res.json().get("elements", [{}])[0].get("tags", {}).get("total", 0)

            metric = LocationMetric(
                sector=sector,
                county=county,
                metric_type="business_density",
                metric_value=float(business_count),
                metric_source=DataSource.osm,
                lat=float(geo.get("lat", 0)),
                lng=float(geo.get("lon", 0))
            )
            db.add(metric)
            count += 1
        except Exception as e:
            print(f"Location error {county}: {e}")

    db.commit()
    return count

def seed_fmcg_catalog(db: Session) -> int:
    """Seed FMCG from OpenFoodFacts API. Zero setup for users"""
    count = 0
    categories = ["maize flour", "rice", "cooking oil", "milk", "sugar"]

    for cat in categories:
        try:
            url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={cat}&json=true&page_size=20"
            res = requests.get(url, timeout=10)
            products = res.json().get("products", [])

            for p in products:
                product = FMCGCatalog(
                    category="Food & Staples",
                    subcategory=cat,
                    product_name=p.get("product_name", "Unknown"),
                    brand=p.get("brands", "Unknown"),
                    barcode=p.get("code"),
                    source=DataSource.openfoodfacts
                )
                db.merge(product)
                count += 1
        except:
            continue

    db.commit()
    return count
def get_demand_signal(data):
    return {"demand": 0}

def get_price_stats(data):
    return {"avg_price": 0}
