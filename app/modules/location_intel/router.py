from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import (
    get_county_comparison,
    generate_heatmap,
    fetch_osm_businesses,
    calculate_price_arbitrage
)
from.models import LocationComparison, OpportunityHeatmap, PriceArbitrage, KENYA_COUNTIES
from app.modules.db import get_db

router = APIRouter()

class ComparisonRequest(BaseModel):
    sector: str
    location_a: str
    location_b: str
    location_type: str = "county"

class HeatmapResponse(BaseModel):
    county: str
    opportunity_score: float
    lat: Optional[float]
    lng: Optional[float]
    factors: dict

@router.get("/counties")
def list_counties():
    """Return all 47 Kenya counties for dropdowns"""
    return {"counties": KENYA_COUNTIES}

@router.post("/compare") # response_model removed temporarily
def compare_locations(request: ComparisonRequest, db: Session = Depends(get_db)):
    """Compare 2 counties/constituencies for a sector. Powers Insight Page"""
    if request.location_a not in KENYA_COUNTIES or request.location_b not in KENYA_COUNTIES:
        raise HTTPException(status_code=404, detail="County not found")

    result = get_county_comparison(db, request.sector, request.location_a, request.location_b)
    return result

@router.get("/heatmap/{sector}", response_model=List[HeatmapResponse])
def get_heatmap(
    sector: str,
    urban_rural: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get opportunity heatmap 0-100 for all counties. Powers Home Dashboard County Heatmap"""
    heatmap_data = generate_heatmap(db, sector, urban_rural)
    return heatmap_data

@router.get("/arbitrage")
def get_arbitrage(
    product: str = Query(...),
    db: Session = Depends(get_db)
):
    """Show price gaps between counties. Powers Price Arbitrage Maps for wholesalers"""
    results = calculate_price_arbitrage(db, product)
    return {
        "product": product,
        "arbitrage_opportunities": [
            {
                "from": r.county_from,
                "to": r.county_to,
                "price_gap_kes": r.price_gap_kes,
                "margin_percent": r.margin_percent
            } for r in results
        ]
    }

@router.get("/businesses/osm")
def get_osm_businesses(
    sector: str = Query(...),
    county: str = Query(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Fetch competitor locations from OSM Overpass API. Powers Competitor Tracker"""
    businesses = fetch_osm_businesses(sector, county)
    return {
        "county": county,
        "sector": sector,
        "competitors": businesses
    }

@router.post("/heatmap/regenerate")
def regenerate_heatmap(background_tasks: BackgroundTasks, sector: str, db: Session = Depends(get_db)):
    """Admin endpoint. Regenerate heatmap for a sector weekly"""
    background_tasks.add_task(generate_heatmap, db, sector)
    return {"message": f"Regenerating heatmap for {sector}"}
