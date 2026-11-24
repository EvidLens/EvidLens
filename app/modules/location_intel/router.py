from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi import BackgroundTasks
from fastapi import Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from sqlmodel import select
from pydantic import BaseModel
from typing import Optional

from .service import get_location_comparison
from .service import generate_heatmap
from .service import fetch_osm_businesses
from .service import calculate_price_arbitrage
from .service import seed_geo_data
from app.modules.location_intel.models import KENYA_COUNTIES
from app.modules.location_intel.models import LocationGeo
from app.core.db import get_session as get_db
from app.core.guards import require_module

router = APIRouter(prefix="/location", tags=["Location Intel"])
templates = Jinja2Templates(directory="app/templates")

class ComparisonRequest(BaseModel):
    sector: str
    location_a: str
    location_b: str
    location_type: str

@router.get("/counties", response_class=HTMLResponse)
async def counties_page(request: Request, db: Session = Depends(get_db)):
    from collections import Counter
    from app.core.models import MarketMetric
    from app.core.models import PriceData
    from app.core.models import Company
    counts = Counter()
    try:
        rows = db.exec(select(MarketMetric.county)).all()
        for r in rows:
            v = r[0] if isinstance(r, (list, tuple)) else getattr(r, 'county', None)
            if v:
                counts[v] += 1
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    try:
        rows = db.exec(select(PriceData.county)).all()
        for r in rows:
            v = r[0] if isinstance(r, (list, tuple)) else getattr(r, 'county', None)
            if v:
                counts[v] += 1
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    try:
        rows = db.exec(select(Company.county)).all()
        for r in rows:
            v = r[0] if isinstance(r, (list, tuple)) else getattr(r, 'county', None)
            if v:
                counts[v] += 1
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    if not counts:
        counts = Counter(
            {
                "Nairobi": 12,
                "Nyeri": 8,
                "Kirinyaga": 6,
                "Kiambu": 9,
                "Nakuru": 7,
                "Kisumu": 5,
                "Mombasa": 6,
                "Muranga": 5,
                "Kakamega": 4,
                "Machakos": 4,
            }
        )
    counties = []
    for name, cnt in counts.most_common(20):
        counties.append(
            {
                "name": name,
                "county": name,
                "count": cnt,
                "market_size": cnt * 50000,
                "business_count": cnt,
            }
        )
    return templates.TemplateResponse(
        "location_counties.html",
        {
            "request": request,
            "counties": counties,
            "data": {"counties": counties},
            "current_user": None,
            "user": None,
        }
    )

@router.get("/geo/counties")
def list_counties():
    return {"country": "Kenya", "counties": KENYA_COUNTIES}

@router.get("/geo/subcounties")
@require_module(module_number=4)
def list_subcounties(request: Request, county: str = Query(...), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level == "subcounty", LocationGeo.parent == county)
    results = db.exec(stmt).all()
    return {"county": county, "subcounties": [r.name for r in results]}

@router.get("/geo/wards")
@require_module(module_number=4)
def list_wards(request: Request, subcounty: str = Query(...), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level == "ward", LocationGeo.parent == subcounty)
    results = db.exec(stmt).all()
    return {"subcounty": subcounty, "wards": [r.name for r in results]}

@router.get("/geo/towns")
@require_module(module_number=4)
def list_towns(request: Request, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level == "town")
    if county:
        stmt = stmt.where(LocationGeo.parent == county)
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

@router.get("/api/heatmap")
@require_module(module_number=4)
def get_heatmap(sector: str = Query(...), metric: str = "business_density", db: Session = Depends(get_db)):
    return generate_heatmap(sector, metric, db)

@router.get("/api/osm")
@require_module(module_number=4)
def get_osm_businesses(county: str = Query(...), category: str = "retail", db: Session = Depends(get_db)):
    return fetch_osm_businesses(county, category, db)

@router.get("/api/arbitrage")
@require_module(module_number=4)
def get_arbitrage(product: str = Query(...), db: Session = Depends(get_db)):
    return calculate_price_arbitrage(product, db)
