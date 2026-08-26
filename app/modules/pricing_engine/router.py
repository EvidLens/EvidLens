from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from typing import Optional

from app.modules.database import get_session
from app.modules.pricing_engine.service import get_price_oracle_data, search_market, get_dashboard_stats
from app.modules.pricing_engine.models import ProductPrice

router = APIRouter(prefix="/market/prices", tags=["Price Oracle"])
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
def price_page(request: Request):
    return templates.TemplateResponse("market_prices.html", {"request": request})

@router.get("/api/search")
def api_search(q: str, sector: str, county: str, db: Session = Depends(get_session)):
    return search_market(db, q, sector, county)

@router.get("/api/oracle")
def api_oracle(product: str, county: Optional[str] = None, db: Session = Depends(get_session)):
    return get_price_oracle_data(db, product, county)

@router.get("/api/stats")
def api_stats(db: Session = Depends(get_session)):
    return get_dashboard_stats(db)

@router.get("/sync-real")
def sync_real(db: Session = Depends(get_session)):
    """REAL: MarketMetric -> ProductPrice + Competitor"""
    from sqlmodel import select
    from app.core.models import MarketMetric, KenyaLensBusiness

    metrics = db.exec(select(MarketMetric).limit(500)).all()
    businesses = db.exec(select(KenyaLensBusiness).limit(500)).all()

    inserted_price = 0
    for m in metrics:
        if not m.product or not m.avg_price_kes:
            continue
        exists = db.exec(select(ProductPrice).where(ProductPrice.product_name == m.product, ProductPrice.county == m.county)).first()
        if not exists:
            db.add(ProductPrice(product_name=m.product, price_kes=float(m.avg_price_kes), county=m.county or "Nairobi", unit="pcs"))
            inserted_price += 1

    inserted_comp = 0
    for b in businesses:
        from app.modules.pricing_engine.models import Competitor
        exists = db.exec(select(Competitor).where(Competitor.name == b.name)).first()
        if not exists:
            db.add(Competitor(name=b.name, sector=b.sector or "General", county=b.county or "Nairobi", lat=b.lat or 0, lng=b.lng or 0))
            inserted_comp += 1

    db.commit()
    return {"product_price_inserted": inserted_price, "competitor_inserted": inserted_comp}
