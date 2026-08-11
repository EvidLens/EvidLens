from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.modules.database import get_session as get_db
from app.modules.market_engine.service import MarketEngineService

router = APIRouter(prefix="/api/market", tags=["Market Engine"])

def get_service(db: Session = Depends(get_db)):
    return MarketEngineService(db)

@router.post("/search")
async def search_market(data: dict, service: MarketEngineService = Depends(get_service)):
    return await service.search_market(data["q"], data["sector"], data["county"])

@router.post("/analyze")
async def analyze(data: dict, service: MarketEngineService = Depends(get_service)):
    return await service.analyze_with_ai(data["sector"], data["county"])

@router.get("/dashboard-stats")
async def dashboard_stats(service: MarketEngineService = Depends(get_service)):
    return await service.get_dashboard_stats()

@router.post("/terminal")
async def terminal(data: dict, service: MarketEngineService = Depends(get_service)):
    return await service.get_real_time_terminal(data["sector"], data["county"])

@router.post("/competitors")
async def competitors(data: dict, service: MarketEngineService = Depends(get_service)):
    return await service.get_competitor_overview(data["sector"], data["county"])
