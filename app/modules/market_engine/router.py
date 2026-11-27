from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, desc
from datetime import datetime, timedelta, timezone
import logging

from app.core.db import get_session
from app.core.models import MarketMetric, NewsArticle, ExportOpportunity

router = APIRouter(prefix="/market", tags=["Market"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc
logger = logging.getLogger("evidlens.market")

DISPLAY_SOURCE = "Live Market Data"

async def _get_user(request: Request, db: Session):
    try:
        from app.modules.auth.dependencies import get_current_user
        return await get_current_user(request, db)
    except Exception:
        return None

def _latest_per_product_county(rows):
    seen = {}
    for p in rows:
        key = (
            (getattr(p, 'product', '') or '').strip().lower(),
            (getattr(p, 'county', '') or '').strip().lower(),
        )
        if key not in seen:
            seen[key] = p
    return list(seen.values())

def _is_uniform_72(values):
    vals = [v for v in values if v is not None]
    if len(vals) < 3:
        return False
    try:
        count_72 = sum(1 for v in vals if float(v) == 72.0)
    except Exception:
        return False
    return (count_72 / len(vals)) >= 0.8

def _clean_demand(value, uniform_72=False):
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if v < 0 or v > 100:
        return None
    if uniform_72 and v == 72.0:
        return None
    return round(v, 1)

def _risk_level(title: str, category: str, summary: str) -> str:
    text = f"{title or ''} {category or ''} {summary or ''}".lower()
    if any(k in text for k in ["ban", "shutdown", "outbreak", "drought", "crisis", "sanction", "recall"]):
        return "HIGH"
    if any(k in text for k in ["deadline", "tax", "regulation", "rate hike", "shortage", "delay", "fine"]):
        return "MEDIUM"
    return "LOW"

def _fmt_date(dt):
    if not dt:
        return ""
    try:
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(dt)

@router.get("/prices", response_class=HTMLResponse)
async def prices_page(request: Request, q: str = None, county: str = None, sector: str = None, db: Session = Depends(get_session)):
    prices = []
    try:
        rows = db.exec(select(MarketMetric).order_by(desc(MarketMetric.created_at)).limit(500)).all()
        rows = _latest_per_product_county(rows)
        uniform_72 = _is_uniform_72([getattr(p, 'demand_score', None) for p in rows])
        for p in rows:
            if q and q.lower() not in (getattr(p, 'product', '') or '').lower():
                continue
            if county and county.lower() not in (getattr(p, 'county', '') or '').lower():
                continue
            if sector and sector.lower() not in (getattr(p, 'sector', '') or '').lower():
                continue
            price = getattr(p, 'avg_price_kes', None)
            demand = _clean_demand(getattr(p, 'demand_score', None), uniform_72=uniform_72)
            created = getattr(p, 'created_at', '')
            prices.append({
                "product_name": getattr(p, 'product', 'Product') or 'Product',
                "product": getattr(p, 'product', 'Product') or 'Product',
                "county": getattr(p, 'county', 'Kenya') or 'Kenya',
                "sector": getattr(p, 'sector', 'Agriculture') or 'Agriculture',
                "price": price,
                "avg_price_kes": price,
                "demand_score": demand,
                "demand": demand,
                "created_at": created,
                "updated_at": created,
                "updated_label": _fmt_date(created),
                "source": DISPLAY_SOURCE,
            })
    except Exception as e:
        logger.exception(f"prices_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        prices = []

    current_user = await _get_user(request, db)
    return templates.TemplateResponse(
        "market_prices.html",
        {"request": request, "prices": prices, "has_data": len(prices) > 0, "q": q or "", "county": county or "", "sector": sector or "", "current_user": current_user, "user": current_user}
    )

@router.get("/demand", response_class=HTMLResponse)
async def demand_page(request: Request, db: Session = Depends(get_session)):
    demand = []
    try:
        rows = db.exec(select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
        rows = _latest_per_product_county(rows)
        uniform_72 = _is_uniform_72([getattr(p, 'demand_score', None) for p in rows])
        for d in rows:
            score = _clean_demand(getattr(d, 'demand_score', None), uniform_72=uniform_72)
            if score is None:
                continue
            demand.append({
                "product": getattr(d, 'product', 'Product') or 'Product',
                "county": getattr(d, 'county', 'Kenya') or 'Kenya',
                "sector": getattr(d, 'sector', 'Agriculture') or 'Agriculture',
                "score": score,
                "demand_score": score,
                "price": getattr(d, 'avg_price_kes', None),
                "avg_price_kes": getattr(d, 'avg_price_kes', None),
                "source": DISPLAY_SOURCE,
            })
    except Exception as e:
        logger.exception(f"demand_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        demand = []

    current_user = await _get_user(request, db)
    return templates.TemplateResponse(
        "market_demand.html",
        {"request": request, "demand": demand, "data": demand, "has_data": len(demand) > 0, "current_user": current_user, "user": current_user}
    )

@router.get("/risk", response_class=HTMLResponse)
async def risk_page(request: Request, db: Session = Depends(get_session)):
    alerts = []
    try:
        since = datetime.now(UTC) - timedelta(days=14)
        rows = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
        for n in rows:
            title = getattr(n, 'title', 'Alert') or 'Alert'
            summary = getattr(n, 'summary', '') or ''
            if not summary or summary.strip().lower() == title.strip().lower():
                summary = getattr(n, 'category', '') or 'Market update - see source for details.'
            source = getattr(n, 'source', '') or DISPLAY_SOURCE
            if source.strip().lower() == "evidlens":
                source = "Curated by EvidLens"
            alerts.append({
                "title": title,
                "summary": summary,
                "source": source,
                "published_at": getattr(n, 'published_at', '') or '',
                "published_label": _fmt_date(getattr(n, 'published_at', None)),
                "category": getattr(n, 'category', '') or '',
                "level": _risk_level(title, getattr(n, 'category', ''), summary),
            })
    except Exception as e:
        logger.exception(f"risk_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        alerts = []

    current_user = await _get_user(request, db)
    return templates.TemplateResponse(
        "market_risk.html",
        {"request": request, "risk_alerts": alerts, "alerts": alerts, "has_data": len(alerts) > 0, "current_user": current_user, "user": current_user}
    )

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_session)):
    exports = []
    try:
        rows = db.exec(select(ExportOpportunity).order_by(desc(ExportOpportunity.created_at)).limit(100)).all()
        for x in rows:
            exports.append({
                "product": getattr(x, 'product', 'Product') or 'Product',
                "country": getattr(x, 'country', 'Kenya') or 'Kenya',
                "destination": getattr(x, 'country', 'Kenya') or 'Kenya',
                "opportunity_score": getattr(x, 'opportunity_score', None),
                "county": getattr(x, 'county', '') or '',
                "created_at": getattr(x, 'created_at', '') or '',
            })
    except Exception as e:
        logger.exception(f"export_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        exports = []

    current_user = await _get_user(request, db)
    return templates.TemplateResponse(
        "market_export.html",
        {"request": request, "exports": exports, "data": exports, "has_data": len(exports) > 0, "current_user": current_user, "user": current_user}
    )

@router.get("/api/prices")
async def get_prices(product: str = None, county: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).order_by(desc(MarketMetric.created_at))
    if product:
        q = q.where(MarketMetric.product.ilike(f"%{product}%"))
    if county:
        q = q.where(MarketMetric.county.ilike(f"%{county}%"))
    data = db.exec(q.limit(500)).all()
    uniform_72 = _is_uniform_72([getattr(d, 'demand_score', None) for d in data])
    out = []
    for d in data:
        item = d.model_dump(mode='json')
        item['demand_score'] = _clean_demand(d.demand_score, uniform_72=uniform_72)
        out.append(item)
    return {"total": len(out), "data": out}

@router.get("/api/demand")
async def get_demand(sector: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score))
    if sector:
        q = q.where(MarketMetric.sector.ilike(f"%{sector}%"))
    data = db.exec(q.limit(100)).all()
    uniform_72 = _is_uniform_72([getattr(d, 'demand_score', None) for d in data])
    return {"data": [{"product": d.product, "county": d.county, "sector": d.sector, "score": _clean_demand(d.demand_score, uniform_72=uniform_72), "price": float(d.avg_price_kes) if d.avg_price_kes is not None else None} for d in data]}

@router.get("/api/risk")
async def get_risk(db: Session = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=14)
    news = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
    return {"risk_alerts": [n.model_dump(mode='json') for n in news], "total": len(news)}

@router.get("/api/export")
async def get_export(db: Session = Depends(get_session)):
    data = db.exec(select(ExportOpportunity).order_by(desc(ExportOpportunity.created_at)).limit(100)).all()
    return {"total": len(data), "data": [d.model_dump(mode='json') for d in data]}
