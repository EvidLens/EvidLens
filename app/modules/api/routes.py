from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session
from typing import Optional
from app.core.db import get_session
from app.modules.api.service import APIService

router = APIRouter(prefix="/api", tags=["Public API"])

@router.get("/competitive")
async def get_competitive(sector: str = Query(...), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_competitive(sector, county)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Competitive API failed: {str(e)}")

@router.get("/price-oracle")
async def get_price_oracle(sector: str = Query(...), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_price_oracle(sector, county)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Price Oracle API failed: {str(e)}")

@router.get("/demand")
async def get_demand(sector: str = Query(...), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_demand(sector, county)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demand API failed: {str(e)}")

@router.get("/policy")
async def get_policy(sector: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_policy(sector)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy API failed: {str(e)}")

@router.get("/funding")
async def get_funding(sector: str = Query(...), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_funding(sector)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Funding API failed: {str(e)}")

@router.get("/risk")
async def get_risk(business: str = Query(...), county: str = Query(...), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_risk(business, county)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk API failed: {str(e)}")

@router.get("/export")
async def get_export(sector: str = Query(...), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_export(sector)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export API failed: {str(e)}")

@router.get("/consumer")
async def get_consumer(sector: str = Query(...), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_consumer(sector, county)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consumer API failed: {str(e)}")

@router.get("/county")
async def get_county(county: str = Query(...), db: Session = Depends(get_session)):
    try:
        service = APIService(db)
        return await service.get_county(county)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"County API failed: {str(e)}")
