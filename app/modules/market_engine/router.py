from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.modules.market_engine.service import MarketEngineService

router = APIRouter()

@router.get("/stats")
async def stats(db: Session = Depends(get_session)):
    service = MarketEngineService(db)
    return await service.get_stats()

@router.post("/terminal")
async def terminal(sector: str, county: str = "National", date_range: str = "30d", db: Session = Depends(get_session)):
    service = MarketEngineService(db)
    return await service.real_time_market_terminal(sector, county, date_range)

@router.post("/startups")
async def startups(sector: str, date_range: str = "90d", db: Session = Depends(get_session)):
    service = MarketEngineService(db)
    return await service.startup_tech_tracker(sector, date_range)

@router.post("/intent")
async def intent(sector: str, county: str, keyword: str, db: Session = Depends(get_session)):
    service = MarketEngineService(db)
    return await service.b2b_intent_signals(sector, county, keyword)
