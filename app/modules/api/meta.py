from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.db import get_db
from app.core.models import PriceData, GeoData

router = APIRouter(prefix="/api/meta", tags=["meta"])

@router.get("/sectors")
def get_sectors(db: Session = Depends(get_db)):
    sectors = db.exec(select(PriceData.sector).distinct()).all()
    return {"sectors": [s for s in sectors if s]}

@router.get("/counties")
def get_counties(db: Session = Depends(get_db)):
    counties = db.exec(select(PriceData.county).distinct()).all()
    return {"counties": [c for c in counties if c]}

@router.get("/subcounties")
def get_subcounties(county: str, db: Session = Depends(get_db)):
    subcounties = db.exec(select(GeoData.name).where(GeoData.type == "subcounty" and GeoData.parent == county).distinct()).all()
    return {"subcounties": [s for s in subcounties if s]}
