from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func, or_, desc
from datetime import datetime, timezone

from app.core.models import KenyaLensBusiness, MarketMetric, NewsArticle, SocialMention, Sector, UserSubscription
from app.core.db import get_session
from app.core.service import CoreService
from app.modules.auth.dependencies import get_current_user
from app.core.models import Report, ReportType, ReportFormat, ReportStatus

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
async def dashboard_api(
    db: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    tenant_id = user.tenant_id
    
    user_subs = db.exec(select(UserSubscription).where(UserSubscription.tenant_id == tenant_id)).all()
    active_module_names = [s.module_name for s in user_subs]
    
    business_count = db.exec(select(func.count(KenyaLensBusiness.id))).one()
    metric_count = db.exec(select(func.count(MarketMetric.id))).one()
    news_count = db.exec(select(func.count(NewsArticle.id))).one()
    social_count = db.exec(select(func.count(SocialMention.id))).one()
    subscription_count = db.exec(select(func.count(UserSubscription.id))).one()
    sector_count = db.exec(select(func.count(Sector.id))).one()
    county_count = db.exec(select(func.count(func.distinct(MarketMetric.county)))).one() if metric_count > 0 else 0
    sector_metric_count = db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() if metric_count > 0 else 0
    policy_count = db.exec(select(func.count(NewsArticle.id)).where(NewsArticle.category == "Policy")).one()
    funding_count = db.exec(select(func.count(KenyaLensBusiness.id)).where(or_(KenyaLensBusiness.sector.ilike("%Financial%"), KenyaLensBusiness.sector.ilike("%Banking%"), KenyaLensBusiness.sector.ilike("%Insurance%"), KenyaLensBusiness.sector.ilike("%SACCO%"), KenyaLensBusiness.sector.ilike("%Microfinance%"), KenyaLensBusiness.sector.ilike("%FinTech%")))).one() if business_count > 0 else 0
    
    all_modules = [
        {"id": 1, "name": "Competitive Engine", "icon": "🎯", "count": business_count, "route": "/competitive", "required_module": "Competitive Engine"},
        {"id": 2, "name": "Price Oracle", "icon": "💰", "count": metric_count, "route": "/market/prices", "required_module": "Pricing Engine"},
        {"id": 3, "name": "Demand Radar", "icon": "📈", "count": metric_count, "route": "/market/demand", "required_module": "Market Engine"},
        {"id": 4, "name": "County Mapper", "icon": "🗺️", "count": county_count, "route": "/location/counties", "required_module": "Location Engine"},
        {"id": 5, "name": "Consumer Pulse", "icon": "👥", "count": social_count, "route": "/voice", "required_module": "Consumer Engine"},
        {"id": 6, "name": "Risk Sentinel", "icon": "⚠️", "count": news_count, "route": "/market/risk", "required_module": "Market Engine"},
        {"id": 7, "name": "Policy Watch", "icon": "📜", "count": policy_count, "route": "/kb/policy", "required_module": "Regulatory Engine"},
        {"id": 8, "name": "Funding Radar", "icon": "🏦", "count": funding_count, "route": "/reports/funding", "required_module": "Competitive Engine"},
        {"id": 9, "name": "Export Navigator", "icon": "🚢", "count": 0, "route": "/market/export", "required_module": "Market Engine"},
        #{"id": 10, "name": "KenyaLensIQ", "icon": "📊", "count": 0, "route": "/kenyalensiq", "required_module": "KenyaLensIQ"},
        {"id": 11, "name": "Report Builder", "icon": "📑", "count": subscription_count, "route": "/reports", "required_module": "Report Builder"},
        {"id": 12, "name": "AI Insights", "icon": "🧠", "count": 0, "route": "/ai", "required_module": "AI Insights"}
    ]
    
    modules = []
    for m in all_modules:
        is_active = m["required_module"] in active_module_names
        modules.append({"id": m["id"], "name": m["name"], "icon": m["icon"], "count": m["count"], "route": m["route"], "is_active": is_active, "is_locked": not is_active})
        
    stats = {"insights_generated": metric_count, "sectors_covered": sector_metric_count, "reports_exported": subscription_count, "active_products": metric_count, "businesses": business_count}
    
    trending = []
    if "Market Engine" in active_module_names and metric_count > 0:
        top_demands = db.exec(select(MarketMetric.product, MarketMetric.county, MarketMetric.sector, MarketMetric.demand_score).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score)).limit(3)).all()
        for d in top_demands:
            trending.append({"category": d.sector, "headline": f"{d.product} demand up in {d.county}", "score": d.demand_score, "product": d.product, "county": d.county, "updated": ""})
            
    return {"stats": stats, "trending": trending, "modules": modules, "active_plan_modules": active_module_names, "last_updated": datetime.now(UTC).isoformat()}
