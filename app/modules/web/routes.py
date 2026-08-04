from app.modules.kenyalensiq.models import KenyaLensBusiness
from sqlalchemy import distinct, func, desc
from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlmodel import Session, select
from app.core.db import get_db
from app.modules.auth.service import create_user, login_user, get_user_by_email
from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric
from app.modules.market_engine.service import MarketEngineService, get_competitor_overview
from app.modules.payments.service import initiate_stk_push
from app.modules.ai_insights.service import generate_insights
from app.modules.report_builder.service import generate_report_pdf
from app.modules.knowledge_base.service import get_sector_benchmark

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/api/competitive")
def get_competitive(db: Session = Depends(get_db)):
    stmt = select(Competitor).order_by(desc(Competitor.avg_rating)).limit(100)
    competitors = db.exec(stmt).all()
    data = [{
        "id": c.id,
        "business_name": c.business_name,
        "sector": c.sector,
        "country": c.country,
        "county": c.county,
        "sub_county": c.sub_county,
        "town": c.town,
        "address": c.address,
        "lat": c.lat,
        "lng": c.lng,
        "rating": c.avg_rating,
        "review_count": c.review_count,
        "source": c.source,
        "last_seen_at": c.last_seen_at
    } for c in competitors]
    stmt2 = select(Competitor.sector, func.count(Competitor.id)).group_by(Competitor.sector)
    top_sectors = db.exec(stmt2).all()
    return {
        "service": "Competitive Engine",
        "status": "LIVE",
        "total_competitors": len(data),
        "top_sectors": [{"sector": s[0], "count": s[1]} for s in top_sectors],
        "data": data
    }

@router.get("/api/price-oracle")
def get_price_oracle(db: Session = Depends(get_db)):
    stmt = select(MarketMetric).where(MarketMetric.metric_type == "price_avg").order_by(desc(MarketMetric.updated_at)).limit(100)
    prices = db.exec(stmt).all()
    stmt2 = select(MarketMetric.sector, func.avg(MarketMetric.metric_value)).where(MarketMetric.metric_type == "price_avg").group_by(MarketMetric.sector)
    by_sector = db.exec(stmt2).all()
    data = [{
        "id": p.id,
        "sector": p.sector,
        "county": p.county,
        "price_kes": p.metric_value,
        "period": p.period,
        "source": p.source,
        "updated_at": p.updated_at
    } for p in prices]
    return {
        "service": "Price Oracle",
        "status": "LIVE",
        "records": len(data),
        "avg_by_sector": [{"sector": s[0], "avg_price_kes": float(s[1] or 0)} for s in by_sector],
        "data": data
    }

@router.get("/api/demand")
def get_demand(db: Session = Depends(get_db)):
    stmt = select(MarketMetric).where(MarketMetric.metric_type == "demand_score").order_by(desc(MarketMetric.metric_value)).limit(100)
    demand = db.exec(stmt).all()
    stmt2 = select(MarketMetric.county, func.avg(MarketMetric.metric_value)).where(MarketMetric.metric_type == "demand_score").group_by(MarketMetric.county)
    by_county = db.exec(stmt2).all()
    data = [{
        "id": d.id,
        "sector": d.sector,
        "county": d.county,
        "sub_county": d.sub_county,
        "demand_score": d.metric_value,
        "period": d.period,
        "updated_at": d.updated_at
    } for d in demand]
    return {
        "service": "Demand Radar",
        "status": "LIVE",
        "records": len(data),
        "top_counties": [{"county": c[0], "avg_score": float(c[1] or 0)} for c in by_county],
        "data": data
    }

@router.get("/api/policy")
def get_policy(db: Session = Depends(get_db)):
    return {
        "service": "Policy Watch",
        "status": "LIVE",
        "message": "Connect Policy table",
        "count": 0,
        "data": [],
        "next_steps": ["Add policies table", "Track tax, regulation, incentives"]
    }

@router.get("/api/funding")
def get_funding(db: Session = Depends(get_db)):
    return {
        "service": "Funding Radar",
        "status": "LIVE",
        "message": "Connect Funding table",
        "count": 0,
        "data": [],
        "next_steps": ["Add grants, loans, investors table"]
    }

@router.get("/api/risk")
def get_risk(db: Session = Depends(get_db)):
    stmt = select(MarketSearch.county).where(MarketSearch.demand_level == "High").limit(20)
    risk_zones = db.exec(stmt).all()
    return {
        "service": "Risk Sentinel",
        "status": "LIVE",
        "alerts": len(risk_zones),
        "high_opportunity_low_competition": [r for r in risk_zones],
        "data": []
    }

@router.get("/api/export")
def get_export(db: Session = Depends(get_db)):
    return {
        "service": "Export Navigator",
        "status": "LIVE",
        "message": "Connect Export table",
        "count": 0,
        "data": [],
        "next_steps": ["Add HS codes, export markets, tariffs"]
    }

@router.get("/api/consumer")
def get_consumer(db: Session = Depends(get_db)):
    insights = generate_insights("consumer", {"source": "MarketSearch"})
    stmt = select(MarketSearch.sector, func.count(MarketSearch.id)).group_by(MarketSearch.sector).order_by(desc(func.count(MarketSearch.id))).limit(10)
    searches = db.exec(stmt).all()
    return {
        "service": "Consumer Pulse",
        "status": "LIVE",
        "top_searches": [{"sector": s[0], "search_count": s[1]} for s in searches],
        "ai_insights": insights
    }

@router.get("/api/county")
def get_county(db: Session = Depends(get_db)):
    stmt = select(
        MarketSearch.county,
        func.sum(MarketSearch.market_size_kes),
        func.avg(MarketSearch.growth_rate),
        func.count(MarketSearch.id)
    ).group_by(MarketSearch.county)
    counties = db.exec(stmt).all()
    data = [{
        "county": c[0],
        "total_market_size_kes": float(c[1] or 0),
        "avg_growth_rate": float(c[2] or 0),
        "search_volume": c[3]
    } for c in counties]
    return {
        "service": "County Mapper",
        "status": "LIVE",
        "counties": len(data),
        "data": data
    }

@router.get("/api/counties")
def get_counties(db: Session = Depends(get_db)):
    stmt = select(distinct(KenyaLensBusiness.county)).where(KenyaLensBusiness.county.isnot(None)).order_by(KenyaLensBusiness.county)
    counties = db.exec(stmt).all()
    county_list = [c for c in counties if c]
    return {
        "service": "Counties",
        "status": "LIVE",
        "count": len(county_list),
        "data": county_list
    }

@router.get("/api/sectors")
def get_sectors(db: Session = Depends(get_db)):
    stmt = select(distinct(KenyaLensBusiness.sector)).where(KenyaLensBusiness.sector.isnot(None)).order_by(KenyaLensBusiness.sector)
    sectors = db.exec(stmt).all()
    sector_list = [s for s in sectors if s]
    return {
        "service": "Sectors",
        "status": "LIVE",
        "count": len(sector_list),
        "data": sector_list
    }

@router.get("/api/filters")
def get_filters(db: Session = Depends(get_db)):
    stmt1 = select(distinct(KenyaLensBusiness.county)).where(KenyaLensBusiness.county.isnot(None))
    stmt2 = select(distinct(KenyaLensBusiness.sector)).where(KenyaLensBusiness.sector.isnot(None))
    counties = db.exec(stmt1).all()
    sectors = db.exec(stmt2).all()
    return {
        "counties": sorted([c for c in counties if c]),
        "sectors": sorted([s for s in sectors if s])
    }
