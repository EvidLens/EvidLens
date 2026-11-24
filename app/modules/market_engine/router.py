from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from sqlmodel import select
from sqlmodel import desc
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from app.core.db import get_session
from app.core.models import MarketMetric
from app.core.models import NewsArticle
from app.core.models import ExportOpportunity
from app.core.models import PriceData

router = APIRouter(prefix="/market", tags=["Market"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc

@router.get("/prices", response_class=HTMLResponse)
async def prices_page(request: Request, db: Session = Depends(get_session)):
    prices = []
    try:
        rows = db.exec(select(MarketMetric).order_by(desc(MarketMetric.created_at)).limit(100)).all()
        for p in rows:
            prices.append(
                {
                    "product_name": getattr(p, 'product', 'Product') or 'Product',
                    "product": getattr(p, 'product', 'Product') or 'Product',
                    "county": getattr(p, 'county', 'Kenya') or 'Kenya',
                    "sector": getattr(p, 'sector', 'Agriculture') or 'Agriculture',
                    "price": getattr(p, 'avg_price_kes', 0) or 0,
                    "avg_price_kes": getattr(p, 'avg_price_kes', 0) or 0,
                    "demand_score": getattr(p, 'demand_score', 0) or 0,
                    "created_at": getattr(p, 'created_at', '') or '',
                }
            )
    except Exception as e:
        print(f"prices_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        prices = []
    if not prices:
        prices = [
            {"product_name": "Maize", "product": "Maize", "county": "Nyeri", "sector": "Agriculture", "price": 6500, "avg_price_kes": 6500, "demand_score": 82, "created_at": ""},
            {"product_name": "Tea", "product": "Tea", "county": "Kirinyaga", "sector": "Agriculture", "price": 420, "avg_price_kes": 420, "demand_score": 78, "created_at": ""},
            {"product_name": "Coffee", "product": "Coffee", "county": "Nyeri", "sector": "Agriculture", "price": 8500, "avg_price_kes": 8500, "demand_score": 85, "created_at": ""},
            {"product_name": "Avocado", "product": "Avocado", "county": "Muranga", "sector": "Agriculture", "price": 45, "avg_price_kes": 45, "demand_score": 88, "created_at": ""},
        ]
    return templates.TemplateResponse(
        "market_prices.html",
        {"request": request, "prices": prices, "current_user": None, "user": None}
    )

@router.get("/demand", response_class=HTMLResponse)
async def demand_page(request: Request, db: Session = Depends(get_session)):
    demand = []
    try:
        rows = db.exec(select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
        for d in rows:
            demand.append(
                {
                    "product": getattr(d, 'product', 'Product') or 'Product',
                    "county": getattr(d, 'county', 'Kenya') or 'Kenya',
                    "sector": getattr(d, 'sector', 'Agriculture') or 'Agriculture',
                    "score": float(getattr(d, 'demand_score', 0) or 0),
                    "demand_score": float(getattr(d, 'demand_score', 0) or 0),
                    "price": float(getattr(d, 'avg_price_kes', 0) or 0),
                    "avg_price_kes": float(getattr(d, 'avg_price_kes', 0) or 0),
                }
            )
    except Exception as e:
        print(f"demand_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        demand = []
    if not demand:
        demand = [
            {"product": "Maize", "county": "Nyeri", "sector": "Agriculture", "score": 82, "demand_score": 82, "price": 6500, "avg_price_kes": 6500},
            {"product": "Avocado", "county": "Muranga", "sector": "Agriculture", "score": 88, "demand_score": 88, "price": 45, "avg_price_kes": 45},
        ]
    return templates.TemplateResponse(
        "market_demand.html",
        {"request": request, "demand": demand, "data": demand, "current_user": None, "user": None}
    )

@router.get("/risk", response_class=HTMLResponse)
async def risk_page(request: Request, db: Session = Depends(get_session)):
    alerts = []
    try:
        since = datetime.now(UTC) - timedelta(days=14)
        rows = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
        for n in rows:
            alerts.append(
                {
                    "title": getattr(n, 'title', 'Alert') or 'Alert',
                    "summary": getattr(n, 'summary', '') or '',
                    "source": getattr(n, 'source', '') or '',
                    "published_at": getattr(n, 'published_at', '') or '',
                    "category": getattr(n, 'category', '') or '',
                }
            )
    except Exception as e:
        print(f"risk_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        alerts = []
    return templates.TemplateResponse(
        "market_risk.html",
        {"request": request, "risk_alerts": alerts, "alerts": alerts, "current_user": None, "user": None}
    )

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_session)):
    exports = []
    try:
        rows = db.exec(select(ExportOpportunity).order_by(desc(ExportOpportunity.created_at)).limit(100)).all()
        for x in rows:
            exports.append(
                {
                    "product": getattr(x, 'product', 'Product') or 'Product',
                    "country": getattr(x, 'country', 'Kenya') or 'Kenya',
                    "opportunity_score": getattr(x, 'opportunity_score', 0) or 0,
                    "county": getattr(x, 'county', '') or '',
                    "created_at": getattr(x, 'created_at', '') or '',
                }
            )
    except Exception as e:
        print(f"export_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        exports = []
    if not exports:
        exports = [
            {"product": "Tea", "country": "UK", "opportunity_score": 85, "county": "Kericho", "created_at": ""},
            {"product": "Coffee", "country": "Germany", "opportunity_score": 82, "county": "Nyeri", "created_at": ""},
            {"product": "Avocado", "country": "Netherlands", "opportunity_score": 88, "county": "Muranga", "created_at": ""},
            {"product": "Macadamia", "country": "China", "opportunity_score": 79, "county": "Kirinyaga", "created_at": ""},
        ]
    return templates.TemplateResponse(
        "market_export.html",
        {"request": request, "exports": exports, "data": exports, "current_user": None, "user": None}
    )

@router.get("/api/prices")
async def get_prices(product: str = None, county: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).order_by(desc(MarketMetric.created_at))
    if product:
        q = q.where(MarketMetric.product.ilike(f"%{product}%"))
    if county:
        q = q.where(MarketMetric.county.ilike(f"%{county}%"))
    data = db.exec(q.limit(500)).all()
    return {"total": len(data), "data": [d.model_dump(mode='json') for d in data]}

@router.get("/api/demand")
async def get_demand(sector: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score))
    if sector:
        q = q.where(MarketMetric.sector.ilike(f"%{sector}%"))
    data = db.exec(q.limit(100)).all()
    return {"data": [{"product": d.product, "county": d.county, "sector": d.sector, "score": float(d.demand_score), "price": float(d.avg_price_kes)} for d in data]}

@router.get("/api/risk")
async def get_risk(db: Session = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=14)
    news = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
    return {"risk_alerts": [n.model_dump(mode='json') for n in news], "total": len(news)}

@router.get("/api/export")
async def get_export(db: Session = Depends(get_session)):
    data = db.exec(select(ExportOpportunity).order_by(desc(ExportOpportunity.created_at)).limit(100)).all()
    return {"total": len(data), "data": [d.model_dump(mode='json') for d in data]}
