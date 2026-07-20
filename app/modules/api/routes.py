from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.modules.database import get_session
from app.modules.api.service import APIService

router = APIRouter()

@router.get("/competitive")
async def get_competitive(sector: str, county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_competitive(sector, county)

@router.get("/price-oracle")
async def get_price_oracle(sector: str, county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_price_oracle(sector, county)

@router.get("/demand")
async def get_demand(sector: str, county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_demand(sector, county)

@router.get("/policy")
async def get_policy(sector: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_policy(sector)

@router.get("/funding")
async def get_funding(sector: str, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_funding(sector)

@router.get("/risk")
async def get_risk(business: str, county: str, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_risk(business, county)

@router.get("/export")
async def get_export(sector: str, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_export(sector)

@router.get("/consumer")
async def get_consumer(sector: str, county: str = None, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_consumer(sector, county)

@router.get("/county")
async def get_county(county: str, db: Session = Depends(get_session)):
    service = APIService(db)
    return await service.get_county(county)
