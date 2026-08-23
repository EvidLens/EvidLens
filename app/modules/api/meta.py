from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, and_
from app.core.db import get_session as get_db
from app.core.models import PriceData, Company

router = APIRouter(prefix="/api/meta", tags=["meta"])

def _clean(rows):
    cleaned = []
    for r in rows:
        if r is None:
            continue
        val = r[0] if isinstance(r, (tuple, list)) else r
        if val and str(val).strip():
            cleaned.append(str(val).strip())
    return cleaned

@router.get("/sectors")
def get_sectors(db: Session = Depends(get_db)):
    sectors = set()
    try:
        sectors.update(_clean(db.exec(select(PriceData.sector).distinct()).all()))
    except:
        pass
    try:
        sectors.update(_clean(db.exec(select(Company.sector).distinct()).all()))
    except:
        pass
    try:
        from app.core.models import SectorReport
        sectors.update(_clean(db.exec(select(SectorReport.sector).distinct()).all()))
    except:
        pass
    try:
        from app.modules.location_intel.models import LocationDemand
        sectors.update(_clean(db.exec(select(LocationDemand.product_category).distinct()).all()))
    except:
        pass
    try:
        from app.modules.location_intel.models import LocationComparison
        sectors.update(_clean(db.exec(select(LocationComparison.sector).distinct()).all()))
    except:
        pass
    return {"sectors": sorted(sectors)}

@router.get("/counties")
def get_counties(db: Session = Depends(get_db)):
    counties = set()
    try:
        counties.update(_clean(db.exec(select(PriceData.county).distinct()).all()))
    except:
        pass
    try:
        counties.update(_clean(db.exec(select(Company.county).distinct()).all()))
    except:
        pass
    try:
        from app.modules.location_intel.models import LocationGeo
        counties.update(_clean(db.exec(select(LocationGeo.name).where(LocationGeo.level == "county").distinct()).all()))
    except:
        pass
    try:
        from app.modules.location_intel.models import LocationDemand
        counties.update(_clean(db.exec(select(LocationDemand.county).distinct()).all()))
    except:
        pass
    return {"counties": sorted(counties)}

@router.get("/subcounties")
def get_subcounties(county: str = Query(...), db: Session = Depends(get_db)):
    subs = set()
    try:
        from app.core.models import GeoData
        stmt = select(GeoData.name).where(and_(GeoData.type == "subcounty", GeoData.parent == county)).distinct()
        subs.update(_clean(db.exec(stmt).all()))
    except:
        pass
    try:
        from app.modules.location_intel.models import LocationGeo
        stmt2 = select(LocationGeo.name).where(and_(LocationGeo.level == "sub_county", LocationGeo.parent == county)).distinct()
        subs.update(_clean(db.exec(stmt2).all()))
    except:
        pass
    try:
        from app.modules.location_intel.models import KENYA_SUBCOUNTIES
        if county in KENYA_SUBCOUNTIES:
            subs.update(KENYA_SUBCOUNTIES[county])
    except:
        pass
    try:
        rows = db.exec(select(Company.subcounty).where(Company.county == county).distinct()).all()
        subs.update(_clean(rows))
    except:
        try:
            rows = db.exec(select(Company.sub_county).where(Company.county == county).distinct()).all()
            subs.update(_clean(rows))
        except:
            pass
    return {"subcounties": sorted(subs)}
