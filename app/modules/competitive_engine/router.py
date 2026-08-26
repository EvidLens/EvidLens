from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from typing import Optional

from app.core.db import engine
from app.modules.database import get_session
from app.modules.competitive_engine.service import CompetitiveEngineService

router = APIRouter(prefix="/competitive", tags=["Competitive Engine"])
templates = Jinja2Templates(directory="app/templates")

def get_service(db: Session = Depends(get_session)):
    return CompetitiveEngineService(db)

@router.get("/", response_class=HTMLResponse)
async def competitive_page(request: Request):
    return templates.TemplateResponse("competitive.html", {"request": request})

@router.get("/api/company")
async def company_db(
    sector: str = Query(..., description="Sector to search"),
    county: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    service: CompetitiveEngineService = Depends(get_service),
):
    return await service.company_deal_database(sector, county, company_name)

@router.get("/api/funding")
async def funding(
    sector: str = Query(...),
    county: Optional[str] = Query(default=None),
    investor: Optional[str] = Query(default=None),
    date_range: str = Query(default="90d"),
    service: CompetitiveEngineService = Depends(get_service),
):
    return await service.funding_tracker(sector, county, investor, date_range)

@router.get("/api/traffic")
async def traffic(
    competitor1: str = Query(...),
    competitor2: str = Query(...),
    service: CompetitiveEngineService = Depends(get_service),
):
    return await service.digital_traffic_analyzer(competitor1, competitor2)

@router.get("/api/monitor")
async def monitor(
    competitor: str = Query(...),
    signal_type: str = Query(..., description="news|sentiment|funding"),
    service: CompetitiveEngineService = Depends(get_service),
):
    return await service.competitor_monitor(competitor, signal_type)

@router.get("/sync-real")
def sync_real(service: CompetitiveEngineService = Depends(get_service)):
    """Populate competitor tables from kenyalens_business - REAL DATA"""
    with Session(engine) as session:
        from sqlmodel import select, func
        from app.core.models import KenyaLensBusiness
        from app.modules.competitive_engine.models import Company

        businesses = session.exec(select(KenyaLensBusiness).limit(500)).all()
        inserted = 0
        for b in businesses:
            exists = session.exec(select(Company).where(Company.name == b.name)).first()
            if not exists:
                session.add(Company(name=b.name, sector=b.sector, county=b.county))
                inserted += 1
        session.commit()
        return {"synced": inserted, "total_business": len(businesses)}
