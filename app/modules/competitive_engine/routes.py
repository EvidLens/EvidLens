from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session  # FIX: was sqlalchemy.orm
from app.modules.database import get_session
from app.modules.competitive_engine.service import CompetitiveEngineService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/competitive", response_class=HTMLResponse)
async def competitive_page(request: Request):
    return templates.TemplateResponse("competitive.html", {"request": request})

@router.get("/api/competitive/company")
async def company_db(sector: str, company_name: str = None, db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.company_deal_database(sector, company_name)

@router.get("/api/competitive/funding")
async def funding(sector: str, investor: str = None, date_range: str = "90d", db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.funding_tracker(sector, investor, date_range)

@router.get("/api/competitive/traffic")
async def traffic(competitor1: str, competitor2: str, date_range: str = "30d", db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.digital_traffic_analyzer(competitor1, competitor2, date_range)

@router.get("/api/competitive/monitor")
async def monitor(competitor: str, signal_type: str, db: Session = Depends(get_session)):
    service = CompetitiveEngineService(db)
    return await service.competitor_monitor(competitor, signal_type)
