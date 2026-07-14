from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import fetch_price_trends, fetch_demand_signals, fetch_location_analytics, seed_fmcg_catalog
from.models import PriceTrend, DemandSignal, LocationMetric, FMCGCatalog
from app.modules.db import get_db
from app.modules.core.guards import require_module, consume_credits

router = APIRouter(prefix="/market-intel", tags=["Market Intel"])

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
@require_module(module_number=1)
def get_price_trends(request: Request, sector: str = Query(...), product: Optional[str] = Query(None), county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(PriceTrend).filter(PriceTrend.sector == sector)
    if product:
        query = query.filter(PriceTrend.product_name.ilike(f"%{product}%"))
    if county:
        query = query.filter(PriceTrend.county == county)
    results = query.order_by(PriceTrend.scraped_at.desc()).limit(100).all()
    if not results:
        raise HTTPException(status_code=404, detail="No price data")
    return results

@router.post("/scrape-prices")
@require_module(module_number=1)
def trigger_price_scrape(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    consume_credits(db, user_id, "api_credits", 2)
    background_tasks.add_task(fetch_price_trends, db)
    return {"message": "Price scraping started"}

@router.get("/demand", response_model=List[DemandResponse])
@require_module(module_number=1)
def get_demand_signals(request: Request, sector: str = Query(...), county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(DemandSignal).filter(DemandSignal.sector == sector)
    if county:
        query = query.filter(DemandSignal.county == county)
    return query.order_by(DemandSignal.recorded_at.desc()).limit(50).all()

@router.post("/refresh-demand")
@require_module(module_number=1)
def refresh_demand(request: Request, sector: str, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    consume_credits(db, user_id, "api_credits", 1)
    count = fetch_demand_signals(db, sector)
    return {"message": f"Fetched {count}"}

@router.get("/location-heatmap")
@require_module(module_number=1)
def get_location_heatmap(request: Request, sector: str = Query(...), metric_type: str = Query("business_density"), db: Session = Depends(get_db)):
    data = db.query(LocationMetric).filter(LocationMetric.sector == sector, LocationMetric.metric_type == metric_type).all()
    return [{"county": d.county, "value": d.metric_value, "lat": d.lat, "lng": d.lng} for d in data]

@router.post("/refresh-location")
@require_module(module_number=1)
def refresh_location(request: Request, sector: str, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    consume_credits(db, user_id, "api_credits", 2)
    count = fetch_location_analytics(db, sector)
    return {"message": f"Updated {count}"}

@router.get("/fmcg-catalog")
def get_fmcg_catalog(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(FMCGCatalog)
    if category:
        query = query.filter(FMCGCatalog.category == category)
    return query.limit(500).all()

@router.post("/seed-fmcg")
def seed_fmcg(db: Session = Depends(get_db)):
    count = seed_fmcg_catalog(db)
    return {"message": f"Seeded {count}"}
