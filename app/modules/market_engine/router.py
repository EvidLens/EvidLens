from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func, desc
from datetime import datetime, timedelta, timezone
from app.core.db import get_session
from app.core.models import MarketMetric, NewsArticle, ExportOpportunity

router = APIRouter(prefix="/market", tags=["Market"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc

@router.get("/prices", response_class=HTMLResponse)
async def prices_page(request: Request): return templates.TemplateResponse("market_prices.html", {"request": request})

@router.get("/demand", response_class=HTMLResponse)
async def demand_page(request: Request): return templates.TemplateResponse("market_demand.html", {"request": request})

@router.get("/risk", response_class=HTMLResponse)
async def risk_page(request: Request): return templates.TemplateResponse("market_risk.html", {"request": request})

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request): return templates.TemplateResponse("market_export.html", {"request": request})

@router.get("/api/prices")
async def get_prices(product: str = None, county: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).order_by(desc(MarketMetric.created_at))
    if product: q = q.where(MarketMetric.product.ilike(f"%{product}%"))
    if county: q = q.where(MarketMetric.county.ilike(f"%{county}%"))
    data = db.exec(q.limit(200)).all()
    return {"total": len(data), "data": [d.model_dump() for d in data]}

@router.get("/api/demand")
async def get_demand(sector: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score))
    if sector: q = q.where(MarketMetric.sector.ilike(f"%{sector}%"))
    data = db.exec(q.limit(50)).all()
    return {"data": [{"product": d.product, "county": d.county, "score": d.demand_score, "price": d.avg_price_kes} for d in data]}

@router.get("/api/risk")
async def get_risk(db: Session = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=7)
    news = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(20)).all()
    risks = [{"title": n.title, "category": n.category, "source": n.source, "url": n.url, "date": n.published_at} for n in news]
    return {"risk_alerts": risks, "total": len(risks)}

@router.get("/api/export")
async def get_export(db: Session = Depends(get_session)):
    data = db.exec(select(ExportOpportunity).order_by(desc(ExportOpportunity.created_at)).limit(50)).all()
    return {"total": len(data), "data": [d.model_dump() for d in data]}
