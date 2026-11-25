from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func, or_, desc
from datetime import datetime, timezone
from typing import Optional

from app.core.models import KenyaLensBusiness, MarketMetric, NewsArticle, SocialMention, UserSubscription, KnowledgeChunk, ExportOpportunity
from app.modules.report_builder.models import Report
from app.core.db import get_session
from app.core.service import CoreService
from app.modules.auth.dependencies import get_current_user
from app.core.gating import PLAN_MODULES, normalize_plan, get_active_plan, get_credits

UTC = timezone.utc
router = APIRouter()

ALL_MODULES = [
    {"id": 1, "name": "Competitive Engine", "icon": "🎯", "route": "/competitive"},
    {"id": 2, "name": "Price Oracle", "icon": "💰", "route": "/market/prices"},
    {"id": 3, "name": "Demand Radar", "icon": "📈", "route": "/market/demand"},
    {"id": 4, "name": "County Mapper", "icon": "🗺️", "route": "/location/counties"},
    {"id": 5, "name": "Consumer Pulse", "icon": "👥", "route": "/voice"},
    {"id": 6, "name": "Risk Sentinel", "icon": "⚠️", "route": "/market/risk"},
    {"id": 7, "name": "Policy Watch", "icon": "📜", "route": "/kb/policy"},
    {"id": 8, "name": "Funding Radar", "icon": "🏦", "route": "/reports/funding"},
    {"id": 9, "name": "Export Navigator", "icon": "🚢", "route": "/market/export"},
    {"id": 10, "name": "Knowledge Base", "icon": "📚", "route": "/kb"},
    {"id": 11, "name": "Report Builder", "icon": "📑", "route": "/reports"},
    {"id": 12, "name": "AI Insights", "icon": "🧠", "route": "/ai"},
]

MODULE_COUNTS = {
    "Competitive Engine": "business",
    "Price Oracle": "metric",
    "Demand Radar": "metric",
    "County Mapper": "county",
    "Consumer Pulse": "social",
    "Risk Sentinel": "news",
    "Policy Watch": "policy",
    "Funding Radar": "funding",
    "Export Navigator": "export",
    "Knowledge Base": "knowledge",
    "Report Builder": "report",
    "AI Insights": "knowledge",
}

@router.get("/api/core/health")
async def health_check(db: Session = Depends(get_session)):
    service = CoreService(db)
    return service.health()

@router.get("/api/core/version")
async def version(db: Session = Depends(get_session)):
    service = CoreService(db)
    return service.version()

@router.get("/api/core/dashboard")
async def dashboard_api(db: Session = Depends(get_session), user=Depends(get_current_user)):
    plan = get_active_plan(db, user)
    active_module_names = PLAN_MODULES.get(plan, PLAN_MODULES["FREE"])
    credits = get_credits(db, user)

    business_count = db.exec(select(func.count(KenyaLensBusiness.id))).one() or 0
    metric_count = db.exec(select(func.count(MarketMetric.id))).one() or 0
    news_count = db.exec(select(func.count(NewsArticle.id))).one() or 0
    social_count = db.exec(select(func.count(SocialMention.id))).one() or 0
    report_count = db.exec(select(func.count(Report.id)).where(Report.user_id == user.id)).one() or 0
    knowledge_count = db.exec(select(func.count(KnowledgeChunk.id))).one() or 0
    export_count = db.exec(select(func.count(ExportOpportunity.id))).one() or 0
    county_count = db.exec(select(func.count(func.distinct(MarketMetric.county)))).one() or 0
    sector_metric_count = db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() or 0
    policy_count = db.exec(select(func.count(NewsArticle.id)).where(NewsArticle.category == "Policy")).one() or 0
    funding_count = db.exec(select(func.count(KenyaLensBusiness.id)).where(or_(
        KenyaLensBusiness.sector.ilike("%Financial%"),
        KenyaLensBusiness.sector.ilike("%Banking%"),
        KenyaLensBusiness.sector.ilike("%Insurance%"),
        KenyaLensBusiness.sector.ilike("%SACCO%"),
        KenyaLensBusiness.sector.ilike("%Microfinance%"),
        KenyaLensBusiness.sector.ilike("%FinTech%")
    ))).one() or 0

    counts = {
        "business": business_count,
        "metric": metric_count,
        "county": county_count,
        "social": social_count,
        "news": news_count,
        "policy": policy_count,
        "funding": funding_count,
        "export": export_count,
        "knowledge": knowledge_count,
        "report": report_count,
    }

    modules = [{
        "id": m["id"],
        "name": m["name"],
        "icon": m["icon"],
        "count": counts.get(MODULE_COUNTS.get(m["name"], "metric"), 0),
        "route": m["route"],
        "required_module": m["name"],
        "is_active": m["name"] in active_module_names,
        "is_locked": m["name"] not in active_module_names,
    } for m in ALL_MODULES]

    stats = {
        "insights_generated": metric_count,
        "sectors_covered": sector_metric_count,
        "reports_exported": report_count,
        "active_products": metric_count,
        "businesses": business_count,
        "credits": credits,
        "plan": plan,
    }

    trending = []
    if metric_count > 0:
        top_demands = db.exec(
            select(MarketMetric.product, MarketMetric.county, MarketMetric.sector, MarketMetric.demand_score)
            .where(MarketMetric.demand_score.isnot(None))
            .order_by(desc(MarketMetric.demand_score)).limit(3)
        ).all()
        for d in top_demands:
            trending.append({
                "category": d.sector,
                "headline": f"{d.product} demand up in {d.county}",
                "score": float(d.demand_score or 0),
                "product": d.product,
                "county": d.county,
                "updated": datetime.now(UTC).isoformat(),
            })

    return {
        "stats": stats,
        "trending": trending,
        "modules": modules,
        "active_plan_modules": active_module_names,
        "plan": plan,
        "credits": credits,
    }
