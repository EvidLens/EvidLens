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

# User-facing label - NEVER expose DB table name like "MarketMetric"
DISPLAY_SOURCE = "Live Market Data"

async def _get_user(request: Request, db: Session):
    """Return real user or None - never crash the page if auth fails."""
    try:
        from app.modules.auth.dependencies import get_current_user
        return await get_current_user(request, db)
    except Exception:
        return None

def _latest_per_product_county(rows):
    # Keep only latest row per (product, county) - fixes Maize x3 duplicates
    seen = {}
    for p in rows:
        key = (
            (getattr(p, 'product', '') or '').strip().lower(),
            (getattr(p, 'county', '') or '').strip().lower(),
        )
        if key not in seen:
            seen[key] = p
    return list(seen.values())

def _clean_demand(value):
    """
    Production rule: demand must be real or None.
    - None stays None -> template shows "-"
    - 72 repeated for every product is a seed bug, treat suspicious uniform 72 as None
      if we cannot verify it. We do NOT invent a new fake number.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if v < 0 or v > 100:
        return None
    return round(v, 1)

def _risk_level(title: str, category: str, summary: str) -> str:
    """Derive risk from content - never hard-code all LOW."""
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
        for p in rows:
            if q and q.lower() not in (getattr(p, 'product', '') or '').lower():
                continue
            if county and county.lower() not in (getattr(p, 'county', '') or '').lower():
                continue
            if sector and sector.lower() not in (getattr(p, 'sector', '') or '').lower():
                continue
            price = getattr(p, 'avg_price_kes', None)
            demand = _clean_demand(getattr(p, 'demand_score', None))
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

    # Empty DB = empty list. Template shows "No live prices yet" - no fake Maize/Tea injected
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
        # De-duplicate per product+county, same as prices
        rows = _latest_per_product_county(rows)
        for d in rows:
            demand.append({
                "product": getattr(d, 'product', 'Product') or 'Product',
                "county": getattr(d, 'county', 'Kenya') or 'Kenya',
                "sector": getattr(d, 'sector', 'Agriculture') or 'Agriculture',
                "score": _clean_demand(getattr(d, 'demand_score', None)),
                "demand_score": _clean_demand(getattr(d, 'demand_score', None)),
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
            # FIX: summary must not just repeat title. If same, use category as fallback.
            if not summary or summary.strip().lower() == title.strip().lower():
                summary = getattr(n, 'category', '') or 'Market update - see source for details.'
            source = getattr(n, 'source', '') or DISPLAY_SOURCE
            # Never show internal "EvidLens" as if it were an external source
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
    return {"total": len(data), "data": [d.model_dump(mode='json') for d in data]}

@router.get("/api/demand")
async def get_demand(sector: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score))
    if sector:
        q = q.where(MarketMetric.sector.ilike(f"%{sector}%"))
    data = db.exec(q.limit(100)).all()
    return {"data": [{"product": d.product, "county": d.county, "sector": d.sector, "score": float(d.demand_score) if d.demand_score is not None else None, "price": float(d.avg_price_kes) if d.avg_price_kes is not None else None} for d in data]}

@router.get("/api/risk")
async def get_risk(db: Session = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=14)
    news = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
    return {"risk_alerts": [n.model_dump(mode='json') for n in news], "total": len(news)}

@router.get("/api/export")
async def get_export(db: Session = Depends(get_session)):
    data = db.exec(select(ExportOpportunity).order_by(desc(ExportOpportunity.created_at)).limit(100)).all()
    return {"total": len(data), "data": [d.model_dump(mode='json') for d in data]}
