from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app.core.db import get_session
from app.modules.competitive_engine.service import CompetitiveEngineService

router = APIRouter(prefix="/competitive", tags=["Competitive Engine"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def competitive_page(request: Request):
    return templates.TemplateResponse("competitive.html", {"request": request})

@router.get("/api/company")
async def company_db(sector: str, county: str = None, company_name: str = None, db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.company_deal_database(sector, county, company_name)

@router.get("/api/funding")
async def funding(sector: str, county: str = None, investor: str = None, date_range: str = "90d", db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.funding_tracker(sector, county, investor, date_range)

@router.get("/api/traffic")
async def traffic(competitor1: str, competitor2: str, db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.digital_traffic_analyzer(competitor1, competitor2)

@router.get("/api/monitor")
async def monitor(competitor: str, signal_type: str, db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.competitor_monitor(competitor, signal_type)
