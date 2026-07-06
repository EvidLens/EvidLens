from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import fetch_price_trends, fetch_demand_signals, fetch_location_analytics, seed_fmcg_catalog
from.models import PriceTrend, DemandSignal, LocationMetric, FMCGCatalog
from app.modules.database import get_db

router = APIRouter()

class PriceTrendResponse(BaseModel):
    product_name: str
    brand: Optional[str]
    price_kes: float
    previous_price_kes: Optional[float]
    price_change_percent: float
    source: str
    county: Optional[str]

class DemandResponse(BaseModel):
    sector: str
    county: Optional[str]
    signal_type: str
    signal_value: float
    period: str

@router.get("/prices", response_model=List[PriceTrendResponse])
def get_price_trends(
    sector: str = Query(...),
    product: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get current KE prices from Jumia/Naivas/Carrefour. Powers Price Arbitrage Maps"""
    query = db.query(PriceTrend).filter(PriceTrend.sector == sector)
    if product:
        query = query.filter(PriceTrend.product_name.ilike(f"%{product}%"))
    if county:
        query = query.filter(PriceTrend.county == county)

    results = query.order_by(PriceTrend.scraped_at.desc()).limit(100).all()
    if not results:
        raise HTTPException(status_code=404, detail="No price data. Run /scrape-prices first")
    return results

@router.post("/scrape-prices")
def trigger_price_scrape(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Weekly cron job to scrape Jumia/Naivas/Carrefour"""
    background_tasks.add_task(fetch_price_trends, db)
    return {"message": "Price scraping started. Data will update in ~5 minutes"}

@router.get("/demand", response_model=List[DemandResponse])
def get_demand_signals(
    sector: str = Query(...),
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get demand signals from KNBS + Google Trends"""
    query = db.query(DemandSignal).filter(DemandSignal.sector == sector)
    if county:
        query = query.filter(DemandSignal.county == county)
    return query.order_by(DemandSignal.recorded_at.desc()).limit(50).all()

@router.post("/refresh-demand")
def refresh_demand(sector: str, db: Session = Depends(get_db)):
    """Fetch latest demand data"""
    count = fetch_demand_signals(db, sector)
    return {"message": f"Fetched {count} new demand signals"}

@router.get("/location-heatmap")
def get_location_heatmap(
    sector: str = Query(...),
    metric_type: str = Query("business_density"),
    db: Session = Depends(get_db)
):
    """County x Sector data for heatmaps. Powers Lane 6"""
    data = db.query(LocationMetric).filter(
        LocationMetric.sector == sector,
        LocationMetric.metric_type == metric_type
    ).all()
    return [{"county": d.county, "value": d.metric_value, "lat": d.lat, "lng": d.lng} for d in data]

@router.post("/refresh-location")
def refresh_location(sector: str, db: Session = Depends(get_db)):
    """Fetch OSM + LocationIQ data for sector"""
    count = fetch_location_analytics(db, sector)
    return {"message": f"Updated {count} location metrics"}

@router.get("/fmcg-catalog")
def get_fmcg_catalog(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Full FMCG catalog. Preloaded for Zero Setup"""
    query = db.query(FMCGCatalog)
    if category:
        query = query.filter(FMCGCatalog.category == category)
    return query.limit(500).all()

@router.post("/seed-fmcg")
def seed_fmcg(db: Session = Depends(get_db)):
    """One-time seed from OpenFoodFacts API"""
    count = seed_fmcg_catalog(db)
    return {"message": f"Seeded {count} FMCG products"}
