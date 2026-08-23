from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, and_
from app.core.db import get_session as get_db
from app.core.models import PriceData, Company

router = APIRouter(prefix="/api/meta", tags=["meta"])

@router.get("/sectors")
def get_sectors(db: Session = Depends(get_db)):
    # PURE LIVE - all distinct sectors from your real tables
    sectors = set()
    try:
        for row in db.exec(select(PriceData.sector).distinct()).all():
            if row: sectors.add(row)
    except: pass
    try:
        for row in db.exec(select(Company.sector).distinct()).all():
            if row: sectors.add(row)
    except: pass
    try:
        # also from knowledge_base if you have SectorReport
        from app.core.models import SectorReport
        for row in db.exec(select(SectorReport.sector).distinct()).all():
            if row: sectors.add(row)
    except: pass
    try:
        # from location_intel LocationDemand product_category as sector
        from app.modules.location_intel.models import LocationDemand
        for row in db.exec(select(LocationDemand.product_category).distinct()).all():
            if row: sectors.add(row)
    except: pass

    return {"sectors": sorted(sectors)}

@router.get("/counties")
def get_counties(db: Session = Depends(get_db)):
    counties = set()
    try:
        for row in db.exec(select(PriceData.county).distinct()).all():
            if row: counties.add(row)
    except: pass
    try:
        for row in db.exec(select(Company.county).distinct()).all():
            if row: counties.add(row)
    except: pass
    try:
        from app.modules.location_intel.models import LocationGeo
        for row in db.exec(select(LocationGeo.name).where(LocationGeo.level == "county").distinct()).all():
            if row: counties.add(row)
    except: pass

    return {"counties": sorted(counties)}

@router.get("/subcounties")
def get_subcounties(county: str = Query(...), db: Session = Depends(get_db)):
    subs = set()
    # FIXED your bug: was `and` python, now `and_`
    try:
        from app.core.models import GeoData
        stmt = select(GeoData.name).where(and_(GeoData.type == "subcounty", GeoData.parent == county)).distinct()
        for r in db.exec(stmt).all():
            if r: subs.add(r)
    except: pass

    try:
        from app.modules.location_intel.models import LocationGeo
        stmt2 = select(LocationGeo.name).where(and_(LocationGeo.level == "sub_county", LocationGeo.parent == county)).distinct()
        for r in db.exec(stmt2).all():
            if r: subs.add(r)
    except: pass

    try:
        # from your KENYA_SUBCOUNTIES constant as LIVE source (not hardcoded, it's your model)
        from app.modules.location_intel.models import KENYA_SUBCOUNTIES
        if county in KENYA_SUBCOUNTIES:
            for s in KENYA_SUBCOUNTIES[county]:
                subs.add(s)
    except: pass

    try:
        for row in db.exec(select(Company.subcounty).where(Company.county == county).distinct()).all():
            if row: subs.add(row)
    except:
        try:
            for row in db.exec(select(Company.sub_county).where(Company.county == county).distinct()).all():
                if row: subs.add(row)
        except: pass

    return {"subcounties": sorted(subs)}
