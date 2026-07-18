from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import get_location_comparison, generate_heatmap, fetch_osm_businesses, calculate_price_arbitrage, seed_geo_data
from.models import KENYA_COUNTIES, LocationGeo
from app.modules.database import get_database

router = APIRouter()

class ComparisonRequest(BaseModel):
    sector: str
    location_a: str
    location_b: str
    location_type: str

@router.get("/geo/counties")
def list_counties():
    return {"country": "Kenya", "counties": KENYA_COUNTIES}

@router.get("/geo/subcounties")
def list_subcounties(county: str = Query(...), db: Session = Depends(get_db)):
    results = db.query(LocationGeo).filter(LocationGeo.level=="subcounty", LocationGeo.parent==county).all()
    return {"county": county, "subcounties": [r.name for r in results]}

@router.get("/geo/wards")
def list_wards(subcounty: str = Query(...), db: Session = Depends(get_db)):
    results = db.query(LocationGeo).filter(LocationGeo.level=="ward", LocationGeo.parent==subcounty).all()
    return {"subcounty": subcounty, "wards": [r.name for r in results]}

@router.get("/geo/towns")
def list_towns(county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(LocationGeo).filter(LocationGeo.level=="town")
    if county:
        q = q.filter(LocationGeo.parent==county)
    results = q.all()
    return {"towns": [r.name for r in results]}

@router.post("/geo/seed")
def seed_geo(background_tasks: BackgroundTasks):
    background_tasks.add_task(seed_geo_data)
    return {"status": "seeding_started", "sources": ["OSM Overpass", "IEBC", "KNBS"]}

@router.post("/compare")
def compare_locations(request: ComparisonRequest):
    result = get_location_comparison(request.sector, request.location_a, request.location_b, request.location_type)
    return result
