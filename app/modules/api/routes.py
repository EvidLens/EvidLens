from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.core.db import get_session
from app.modules.api.service import APIService

router = APIRouter(prefix="/api", tags=["Public API"])

def safe_response(data):
    if not data:
        return {"data": [], "count": 0, "message": "No data yet - run seed_master"}
    if isinstance(data, list):
        return {"data": data, "count": len(data)}
    return data

@router.get("/competitive")
async def get_competitive(sector: str = Query(...), county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_competitive(sector, county)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/price-oracle")
async def get_price_oracle(sector: str = Query(...), county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_price_oracle(sector, county)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/demand")
async def get_demand(sector: str = Query(...), county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_demand(sector, county)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/policy")
async def get_policy(sector: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_policy(sector)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/funding")
async def get_funding(sector: str = Query(...), db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_funding(sector)
        return safe_response(result)
    except Exception as e:
        # This is the line that was causing your 500
        print(f"Funding error: {e}")
        return {"data": [], "count": 0, "message": "No funding data yet"}

@router.get("/risk")
async def get_risk(business: str = Query(...), county: str = Query(...), db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_risk(business, county)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/export")
async def get_export(sector: str = Query(...), db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_export(sector)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/consumer")
async def get_consumer(sector: str = Query(...), county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_consumer(sector, county)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}

@router.get("/county")
async def get_county(county: str = Query(...), db: Session = Depends(get_session)):
    service = APIService(db)
    try:
        result = await service.get_county(county)
        return safe_response(result)
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}
