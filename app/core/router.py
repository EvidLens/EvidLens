from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func, or_, desc
from datetime import datetime, timezone

from app.core.db import get_session
from app.core.service import CoreService
from app.modules.core.models import (
    KenyaLensBusiness, MarketMetric, NewsArticle, SocialMention, 
    Sector, UserSubscription
)

UTC = timezone.utc
router = APIRouter()

@router.get("/api/core/health")
async def health_check(db: Session = Depends(get_session)):
    service = CoreService(db)
    return service.health()

@router.get("/api/core/version")
async def version():
    service = CoreService()
    return service.version()

@router.get("/api/core/dashboard")
async def dashboard_api(db: Session = Depends(get_session)):
    business_count = db.exec(select(func.count(KenyaLensBusiness.id))).one()
    metric_count = db.exec(select(func.count(MarketMetric.id))).one()
    news_count = db.exec(select(func.count(NewsArticle.id))).one()
    social_count = db.exec(select(func.count(SocialMention.id))).one()
    subscription_count = db.exec(select(func.count(UserSubscription.id))).one()
    sector_count = db.exec(select(func.count(Sector.id))).one()
    
    county_count = db.exec(select(func.count(func.distinct(MarketMetric.county)))).one() if metric_count > 0 else 0
    sector_metric_count = db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() if metric_count > 0 else 0
    
    try:
        policy_count = db.exec(select(func.count(NewsArticle.id)).where(NewsArticle.category == "Policy")).one()
    except:
        policy_count = 0
        
    funding_count = db.exec(select(func.count(KenyaLensBusiness.id)).where(
        or_(
            KenyaLensBusiness.sector.ilike("%Financial%"),
            KenyaLensBusiness.sector.ilike("%Banking%"),
            KenyaLensBusiness.sector.ilike("%Insurance%"),
            KenyaLensBusiness.sector.ilike("%SACCO%"),
            KenyaLensBusiness.sector.ilike("%Microfinance%"),
            KenyaLensBusiness.sector.ilike("%FinTech%")
        )
    )).one() if business_count > 0 else 0
    
    # Removed KenyaTenant, KenyaLensSurvey, KenyaLensAlert, KenyaLensMember, ExportOpportunity
    # Those models don't exist in new schema. Set to 0
    tenant_count = 0
    survey_count = 0
    alert_count = 0
    member_count = 0
    export_count = 0
    
    lens_count = survey_count
    company_count = business_count
    search_count = metric_count
    
    modules = [
        {"id": 1, "name": "Competitive Engine", "icon": "🎯", "count": company_count, "route": "/competitive"},
        {"id": 2, "name": "Price Oracle", "icon": "💰", "count": metric_count, "route": "/market/prices"},
        {"id": 3, "name": "Demand Radar", "icon": "📈", "count": search_count, "route": "/market/demand"},
        {"id": 4, "name": "County Mapper", "icon": "🗺️", "count": county_count, "route": "/location/counties"},
        {"id": 5, "name": "Consumer Pulse", "icon": "👥", "count": social_count, "route": "/voice"},
        {"id": 6, "name": "Risk Sentinel", "icon": "⚠️", "count": news_count, "route": "/market/risk"},
        {"id": 7, "name": "Policy Watch", "icon": "📜", "count": policy_count, "route": "/kb/policy"},
        {"id": 8, "name": "Funding Radar", "icon": "🏦", "count": funding_count, "route": "/reports/funding"},
        {"id": 9, "name": "Export Navigator", "icon": "🚢", "count": export_count, "route": "/market/export"},
        {"id": 10, "name": "KenyaLensIQ", "icon": "📊", "count": lens_count, "route": "/kenyalensiq"}
    ]
    stats = {
        "insights_generated": search_count,
        "sectors_covered": sector_metric_count,
        "reports_exported": subscription_count,
        "active_products": metric_count,
        "businesses": business_count,
        "surveys": survey_count,
        "alerts": alert_count,
        "members": member_count
    }
    trending = []
    if metric_count > 0:
        top_demands = db.exec(select(MarketMetric.product, MarketMetric.county, MarketMetric.sector, MarketMetric.demand_score).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score)).limit(3)).all()
        for d in top_demands:
            trending.append({"category": d.sector, "headline": f"{d.product} demand up in {d.county}", "score": d.demand_score, "product": d.product, "county": d.county, "updated": ""})
            
    return {"stats": stats, "trending": trending, "modules": modules, "last_updated": datetime.now(UTC).isoformat()}
