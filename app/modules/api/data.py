from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from app.core.db import get_db
from app.core.models import PriceData, Company, MarketMetric

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/prices")
def get_prices(
    db: Session = Depends(get_db),
    search: str = Query(""),
    page: int = 1,
    limit: int = 15,
    sort_by: str = "timestamp",
    order: str = "desc"
):
    q = select(PriceData)
    if search:
        q = q.where(PriceData.product_name.ilike(f"%{search}%") | PriceData.county.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(PriceData)
    if search:
        count_q = count_q.where(PriceData.product_name.ilike(f"%{search}%") | PriceData.county.ilike(f"%{search}%"))
    total = db.exec(count_q).one()

    col = getattr(PriceData, sort_by, PriceData.timestamp)
    q = q.order_by(col.desc() if order == "desc" else col.asc())

    items = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"prices": items, "total": total}

@router.get("/demand")
def get_demand(db: Session = Depends(get_db), search: str = "", page: int = 1, limit: int = 15):
    q = select(MarketMetric)
    count_q = select(func.count()).select_from(MarketMetric)
    if search:
        q = q.where(MarketMetric.product.ilike(f"%{search}%"))
        count_q = count_q.where(MarketMetric.product.ilike(f"%{search}%"))
    total = db.exec(count_q).one()
    items = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"demand": [
        {"product_name": m.product, "sector": m.sector, "county": m.county, "demand_score": m.demand_score or 0, "volume": 0}
        for m in items
    ], "total": total}

@router.get("/companies")
def get_companies(db: Session = Depends(get_db), search: str = "", page: int = 1, limit: int = 15):
    q = select(Company)
    count_q = select(func.count()).select_from(Company)
    if search:
        q = q.where(Company.name.ilike(f"%{search}%") | Company.sector.ilike(f"%{search}%"))
        count_q = count_q.where(Company.name.ilike(f"%{search}%") | Company.sector.ilike(f"%{search}%"))
    total = db.exec(count_q).one()
    items = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": [
        {"name": c.name, "sector": c.sector, "county": c.county, "rating": 0, "reviews": 0, "address": ""}
        for c in items
    ], "total": total}
