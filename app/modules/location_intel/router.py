from fastapi import APIRouter, Depends, Request, BackgroundTasks, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from collections import Counter
import os

from .service import get_location_comparison, generate_heatmap, fetch_osm_businesses, calculate_price_arbitrage, seed_geo_data
from app.modules.location_intel.models import KENYA_COUNTIES, LocationGeo
from app.core.db import get_session as get_db
from app.core.guards import require_module
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/location", tags=["Location Intel"])
templates = Jinja2Templates(directory="app/templates")

def _pick_counties_template():
    if os.path.exists("app/templates/location_counties.html"):
        return "location_counties.html"
    return "location.html"

class ComparisonRequest(BaseModel):
    sector: str
    location_a: str
    location_b: str
    location_type: str

def _clean_county_name(v):
    if not v or not isinstance(v, str):
        return None
    v = v.strip()
    if not v:
        return None
    if v.lower() in ("county", "kenya", "unknown", "null", "none"):
        return None
    return v.title()

@router.get("/counties", response_class=HTMLResponse)
async def counties_page(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None

    counts = Counter()

    def _count_from_query(query):
        try:
            rows = db.exec(query).all()
            for v in rows:
                if isinstance(v, (list, tuple)):
                    v = v[0] if v else None
                elif hasattr(v, "county"):
                    v = getattr(v, "county", None)
                cleaned = _clean_county_name(v)
                if cleaned:
                    counts[cleaned] += 1
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    try:
        from app.core.models import MarketMetric, PriceData, Company
        _count_from_query(select(MarketMetric.county))
        _count_from_query(select(PriceData.county))
        _count_from_query(select(Company.county))
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass

    if not counts:
        counts = Counter({
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
        })

    counties = []
    total_signals = sum(counts.values()) or 1
    total_market_size = 0
    for name, cnt in counts.most_common(20):
        market_size = cnt * 50000
        total_market_size += market_size
        counties.append({
            "name": name,
            "county": name,
            "county_name": name,
            "title": name,
            "count": cnt,
            "business_count": cnt,
            "records": cnt,
            "total_records": cnt,
            "signals": cnt,
            "market_size": market_size,
            "market_size_kes": market_size,
            "size": market_size,
            "share_pct": round((cnt / total_signals) * 100, 1),
        })

    template_name = _pick_counties_template()

    return templates.TemplateResponse(
        template_name,
        {
            "request": request,
            "current_user": current_user,
            "user": current_user,
            "counties": counties,
            "counties_data": counties,
            "county_data": counties,
            "data": counties,
            "count_map": dict(counts),
            "total_counties": len(counties),
            "total_signals": total_signals,
            "total_market_size": total_market_size,
            "active_page": "location",
            "page_title": "County Intelligence",
        },
    )

@router.get("/geo/counties")
def list_counties():
    return {"country": "Kenya", "counties": KENYA_COUNTIES}

@router.get("/geo/subcounties", dependencies=[Depends(require_module(module_number=4))])
def list_subcounties(request: Request, county: str = Query(...), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level == "subcounty", LocationGeo.parent == county)
    results = db.exec(stmt).all()
    return {"county": county, "subcounties": [r.name for r in results]}

@router.get("/geo/wards", dependencies=[Depends(require_module(module_number=4))])
def list_wards(request: Request, subcounty: str = Query(...), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level == "ward", LocationGeo.parent == subcounty)
    results = db.exec(stmt).all()
    return {"subcounty": subcounty, "wards": [r.name for r in results]}

@router.get("/geo/towns", dependencies=[Depends(require_module(module_number=4))])
def list_towns(request: Request, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    stmt = select(LocationGeo).where(LocationGeo.level == "town")
    if county:
        stmt = stmt.where(LocationGeo.parent == county)
    results = db.exec(stmt).all()
    return {"towns": [r.name for r in results]}

@router.post("/geo/seed", dependencies=[Depends(require_module(module_number=4))])
def seed_geo(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(seed_geo_data)
    return {"status": "seeding_started", "sources": ["OSM Overpass", "IEBC", "KNBS"]}

@router.post("/compare", dependencies=[Depends(require_module(module_number=4))])
def compare_locations(request: Request, req: ComparisonRequest):
    result = get_location_comparison(req.sector, req.location_a, req.location_b, req.location_type)
    return result

@router.get("/api/heatmap", dependencies=[Depends(require_module(module_number=4))])
def get_heatmap(sector: str = Query(...), metric: str = "business_density", db: Session = Depends(get_db)):
    return generate_heatmap(sector, metric, db)

@router.get("/api/osm", dependencies=[Depends(require_module(module_number=4))])
def get_osm_businesses(county: str = Query(...), category: str = "retail", db: Session = Depends(get_db)):
    return fetch_osm_businesses(county, category, db)

@router.get("/api/arbitrage", dependencies=[Depends(require_module(module_number=4))])
def get_arbitrage(product: str = Query(...), db: Session = Depends(get_db)):
    return calculate_price_arbitrage(product, db)
