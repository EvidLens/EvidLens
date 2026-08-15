from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from app.core.db import get_db
from app.core.models import Price, Demand, Company

router = APIRouter(prefix="/api/data", tags=["data"])

@router.get("/prices")
def get_prices(
    db: Session = Depends(get_db), 
    search: str = Query(""), 
    page: int = 1, 
    limit: int = 15,
    sort_by: str = "fetched_at",
    order: str = "desc"
):
    q = select(Price)
    if search: 
        q = q.where(Price.product.ilike(f"%{search}%") | Price.county.ilike(f"%{search}%"))
    
    total = db.exec(select(func.count()).select_from(q.subquery())).one()
    
    col = getattr(Price, sort_by, Price.fetched_at)
    q = q.order_by(col.desc() if order == "desc" else col.asc())
        
    items = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"prices": items, "total": total}

@router.get("/demand")
def get_demand(db: Session = Depends(get_db), search: str = "", page: int = 1, limit: int = 15):
    q = select(Demand)
    if search: q = q.where(Demand.product_name.ilike(f"%{search}%"))
    total = db.exec(select(func.count()).select_from(q.subquery())).one()
    items = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"demand": items, "total": total}

@router.get("/companies")
def get_companies(db: Session = Depends(get_db), search: str = "", page: int = 1, limit: int = 15):
    q = select(Company)
    if search: q = q.where(Company.name.ilike(f"%{search}%") | Company.sector.ilike(f"%{search}%"))
    total = db.exec(select(func.count()).select_from(q.subquery())).one()
    items = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": items, "total": total}
