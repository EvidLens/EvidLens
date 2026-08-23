from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, and_
from app.core.db import get_session as get_db
from app.core.models import PriceData, Company
from app.core.models import GeoData as Geo  # if you have GeoData table, else ignore

router = APIRouter(prefix="/api/meta", tags=["meta"])

# FALLBACK - Kenya real data so dropdowns always work even if DB empty
FALLBACK_SECTORS = ["Agriculture","Dairy","Retail","Food Processing","Manufacturing","Services","Technology","Healthcare","Education","Transport","Real Estate","Hospitality","Energy","Construction","Fashion","Finance"]
FALLBACK_COUNTIES = ["Mombasa","Kwale","Kilifi","Tana River","Lamu","Taita-Taveta","Garissa","Wajir","Mandera","Marsabit","Isiolo","Meru","Tharaka-Nithi","Embu","Kitui","Machakos","Makueni","Nyandarua","Nyeri","Kirinyaga","Murang'a","Kiambu","Turkana","West Pokot","Samburu","Trans-Nzoia","Uasin Gishu","Elgeyo-Marakwet","Nandi","Baringo","Laikipia","Nakuru","Narok","Kajiado","Kericho","Bomet","Kakamega","Vihiga","Bungoma","Busia","Siaya","Kisumu","Homa Bay","Migori","Kisii","Nyamira","Nairobi"]
FALLBACK_SUBS = {
    "Nakuru": ["Nakuru East","Nakuru West","Njoro","Molo","Naivasha","Gilgil","Kuresoi North","Kuresoi South","Subukia","Rongai","Bahati"],
    "Nyeri": ["Tetu","Kieni","Mathira","Othaya","Mukurweini","Nyeri Town"],
    "Nairobi": ["Westlands","Dagoretti","Langata","Kibra","Roysambu","Kasarani","Ruaraka","Embakasi","Makadara","Kamukunji","Starehe","Mathare"],
    "Kiambu": ["Gatundu South","Gatundu North","Juja","Thika Town","Ruiru","Githunguri","Kiambu","Kiambaa","Kabete","Kikuyu","Limuru","Lari"],
}

@router.get("/sectors")
def get_sectors(db: Session = Depends(get_db)):
    try:
        # LIVE from PriceData + Company
        sectors_pd = db.exec(select(PriceData.sector).distinct()).all()
        sectors_c = db.exec(select(Company.sector).distinct()).all()
        live = [s for s in (sectors_pd + sectors_c) if s]
        if live:
            return {"sectors": sorted(set(live + FALLBACK_SECTORS))}
    except Exception as e:
        print(f"sectors live failed {e}")
    return {"sectors": FALLBACK_SECTORS}

@router.get("/counties")
def get_counties(db: Session = Depends(get_db)):
    try:
        counties_pd = db.exec(select(PriceData.county).distinct()).all()
        counties_c = db.exec(select(Company.county).distinct()).all()
        live = [c for c in (counties_pd + counties_c) if c]
        if live:
            return {"counties": sorted(set(live + FALLBACK_COUNTIES))}
    except Exception as e:
        print(f"counties live failed {e}")
    return {"counties": FALLBACK_COUNTIES}

@router.get("/subcounties")
def get_subcounties(county: str = Query(...), db: Session = Depends(get_db)):
    # 1. Try GeoData table - FIXED query (was using python `and`)
    try:
        stmt = select(Geo.name).where(and_(Geo.type == "subcounty", Geo.parent == county)).distinct()
        res = db.exec(stmt).all()
        live = [s for s in res if s]
        if live:
            return {"subcounties": sorted(live)}
    except Exception as e:
        print(f"GeoData subcounty failed {e}")
    
    # 2. Try Company subcounty column
    try:
        stmt2 = select(Company.subcounty).where(Company.county == county).distinct()
        res2 = db.exec(stmt2).all()
        live2 = [s for s in res2 if s]
        if live2:
            return {"subcounties": sorted(set(live2))}
    except:
        pass

    # 3. Fallback map - so it NEVER returns []
    return {"subcounties": FALLBACK_SUBS.get(county, ["Central","North","South","East","West","Town"])}

@router.get("/sectors-counties")
def get_all(db: Session = Depends(get_db)):
    return {
        "sectors": get_sectors(db)["sectors"],
        "counties": get_counties(db)["counties"]
    }
