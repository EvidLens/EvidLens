from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modules.data.service import fetch_price_trends, fetch_location_analytics
from app.modules.data.models import PriceTrend, LocationMetric
from.models import CompetitorProfile, CompetitorAlert

def build_battlecard(db: Session, sector: str, competitor_a: str, competitor_b: str):
    fetch_price_trends(db, sector)
    fetch_location_analytics(db, sector)
    
    a_prices = db.query(PriceTrend).filter(PriceTrend.sector==sector, PriceTrend.brand==competitor_a).all()
    b_prices = db.query(PriceTrend).filter(PriceTrend.sector==sector, PriceTrend.brand==competitor_b).all()
    
    a_avg = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector, PriceTrend.brand==competitor_a).scalar() or 0
    b_avg = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector, PriceTrend.brand==competitor_b).scalar() or 0
    
    a_locations = db.query(func.count(LocationMetric.id)).filter(LocationMetric.sector==sector).scalar() or 0
    b_locations = a_locations
    
    price_diff = round(((a_avg - b_avg) / b_avg * 100), 2) if b_avg > 0 else 0
    
    return {
        "sector": sector,
        "competitors": [competitor_a, competitor_b],
        "price_comparison": {
            "competitor_a_avg_kes": float(a_avg),
            "competitor_b_avg_kes": float(b_avg),
            "price_difference_percent": price_diff
        },
        "location_count": {
            "competitor_a": a_locations,
            "competitor_b": b_locations
        },
        "key_gap": "Price and location data comparison complete"
    }

def monitor_competitor(db: Session, sector: str, competitor: str):
    fetch_price_trends(db, sector)
    latest = db.query(PriceTrend).filter(PriceTrend.sector==sector, PriceTrend.brand==competitor).order_by(PriceTrend.scraped_at.desc()).first()
    if not latest:
        return None
    alert = CompetitorAlert(
        sector=sector,
        competitor=competitor,
        alert_type="price_change",
        alert_data={"product": latest.product_name, "price": latest.price_kes, "change": latest.price_change_percent}
    )
    db.add(alert)
    db.commit()
    return alert

def get_competitor_profile(db: Session, sector: str, competitor: str):
    profile = db.query(CompetitorProfile).filter(CompetitorProfile.sector==sector, CompetitorProfile.company_name==competitor).first()
    if not profile:
        return {"sector": sector, "company": competitor, "status": "profile_not_found"}
    return profile
