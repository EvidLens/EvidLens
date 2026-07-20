import os
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any
from .models import PriceTrend, DemandSignal, LocationMetric, ProductCatalog, DataSource

LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_API_KEY")
KNBS_API_URL = os.getenv("KNBS_API_URL", "https://api.knbs.or.ke/v1")

def fetch_price_trends(db: Session, sector: str, keywords: list = None):
    count = 0
    sources = [{"name": "jumia", "url": f"https://www.jumia.co.ke/{sector.lower().replace(' ', '-')}/"}, {"name": "naivas", "url": f"https://www.naivas.online/category/{sector.lower().replace(' ', '-')}"}]
    for src in sources:
        try:
            res = requests.get(src["url"], headers={"User-Agent": "EvidLensBot/1.0"}, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            products = soup.select(".prd")[:50]
            for p in products:
                name = p.select_one(".name").text.strip() if p.select_one(".name") else "Unknown"
                if keywords and not any(k.lower() in name.lower() for k in keywords):
                    continue
                price_text = p.select_one(".prc").text.replace("KSh", "").replace(",", "").strip()
                price = float(price_text) if price_text else 0.0
                prev = db.query(PriceTrend).filter(PriceTrend.product_name == name, PriceTrend.sector==sector).order_by(PriceTrend.scraped_at.desc()).first()
                change = ((price - prev.price_kes) / prev.price_kes * 100) if prev and prev.price_kes else 0.0
                trend = PriceTrend(sector=sector, product_name=name, price_kes=price, previous_price_kes=prev.price_kes if prev else None, price_change_percent=round(change, 2), source=DataSource[src["name"]], county="Nairobi")
                db.merge(trend)
                count += 1
        except:
            pass
    db.commit()
    return count

def fetch_demand_signals(db: Session, sector: str) -> int:
    return 0

def fetch_location_analytics(db: Session, sector: str) -> int:
    return 0

def seed_product_catalog(db: Session, sector: str, category: str = None) -> int:
    count = 0
    search_term = category if category else sector
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={search_term}&json=true&page_size=100"
    return count

def get_demand_signal(db: Session, sector: str, product_or_topic: str, county: str = None):
    return {"demand_score": 50, "trend": "stable"}

def get_price_stats(db: Session, sector: str, product_or_topic: str, county: str = None):
    return {"avg_price": 0, "min_price": 0, "max_price": 0}

def get_aggregated_prices(db: Session, sector: str, county: str) -> List[Dict[str, Any]]:
    return []
