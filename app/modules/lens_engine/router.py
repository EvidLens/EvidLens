from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.core.db import get_session
from app.modules.kenyalensiq.services import LensEngineService

router = APIRouter()

@router.get("/api/lens/insights")
async def get_lens_insights(sector: str = Query(...), county: str = None, db: Session = Depends(get_session)):
    service = LensEngineService(db)
    return await service.generate_sector_insights(sector, county)
