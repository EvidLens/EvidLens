from fastapi import APIRouter, Depends, Header, Request, WebSocket, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional
from.service import get_location_comparison, generate_heatmap, fetch_osm_businesses, calculate_price_arbitrage, seed_geo_data
from app.modules.location_intel.models import KENYA_COUNTIES, LocationGeo
from app.core.db import get_session as get_db
from app.core.guards import require_module

router = APIRouter(prefix="/location", tags=["Location Intel"])

class ComparisonRequest(BaseModel):
    sector: str
    location_a: str
    location_b: str
    location_type: str

@router.get("/geo/counties")
def list_counties():
    return {"country": "Kenya", "counties": KENYA_COUNTIES}

@router.get("/geo/subcounties")
@require_module(module_number=4)
def list_subcounties(request: Request, county: str = Query(...), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level=="subcounty", LocationGeo.parent==county)
    results = db.exec(stmt).all()
    return {"county": county, "subcounties": [r.name for r in results]}

@router.get("/geo/wards")
@require_module(module_number=4)
def list_wards(request: Request, subcounty: str = Query(...), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level=="ward", LocationGeo.parent==subcounty)
    results = db.exec(stmt).all()
    return {"subcounty": subcounty, "wards": [r.name for r in results]}

@router.get("/geo/towns")
@require_module(module_number=4)
def list_towns(request: Request, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level=="town")
    if county:
        stmt = stmt.where(LocationGeo.parent==county)
    results = db.exec(stmt).all()
    return {"towns": [r.name for r in results]}

@router.post("/geo/seed")
@require_module(module_number=4)
def seed_geo(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(seed_geo_data)
    return {"status": "seeding_started", "sources": ["OSM Overpass", "IEBC", "KNBS"]}

@router.post("/compare")
@require_module(module_number=4)
def compare_locations(request: Request, req: ComparisonRequest):
    result = get_location_comparison(req.sector, req.location_a, req.location_b, req.location_type)
    return result
