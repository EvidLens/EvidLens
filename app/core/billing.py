from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlmodel import delete as sql_delete
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import List

from app.core.db import get_session
from app.core.models import UserSubscription
from app.modules.auth.dependencies import get_current_user

UTC = timezone.utc
router = APIRouter(prefix="/api/billing", tags=["billing"])

PLAN_MODULES = {
    "Trial": ["Core OS", "Market Engine", "Consumer Engine", "AI Insights"],
    "Starter": ["Core OS", "Market Engine", "Consumer Engine"],
    "Growth": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine", "Report Builder", "AI Insights"],
    "Pro": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine", "Report Builder", "AI Insights", "Business OS"],
    "Enterprise": ["Core OS", "Market Engine", "Pricing Engine", "Competitive Engine", "Location Engine", "Consumer Engine", "Regulatory Engine", "Report Builder", "AI Insights", "Business OS", "KenyaLensIQ", "Knowledge Base"],
    "EV-FREE": ["Core OS", "Market Engine", "Consumer Engine"],
    "EV-STARTER": ["Core OS", "Market Engine", "Consumer Engine"],
    "EV-SME": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine"],
    "EV-GROWTH": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine", "Report Builder", "AI Insights"],
    "EV-PRO": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine", "Report Builder", "AI Insights", "Business OS"],
    "EV-ENT": ["Core OS", "Market Engine", "Pricing Engine", "Competitive Engine", "Location Engine", "Consumer Engine", "Regulatory Engine", "Report Builder", "AI Insights", "Business OS", "KenyaLensIQ", "Knowledge Base"],
    "starter": ["market_intel", "consumer_insights"],
    "growth": ["market_intel", "competitive_intel", "consumer_insights", "pricing_intel", "location_intel", "ai_insights", "report_builder"],
    "enterprise": ["market_intel", "competitive_intel", "consumer_insights", "pricing_intel", "regulatory_intel", "location_intel", "report_builder", "ai_insights", "business_os", "payments", "kenyalens_iq", "knowledge_base"],
    "trial": ["market_intel", "consumer_insights", "ai_insights"],
    "pro": ["market_intel", "competitive_intel", "consumer_insights", "pricing_intel", "location_intel", "ai_insights", "report_builder", "business_os"],
}

PLAN_DAYS = {"Trial": 7, "Starter": 30, "Growth": 30, "Pro": 30, "Enterprise": 30, "EV-FREE": 7, "EV-STARTER": 30, "EV-SME": 30, "EV-GROWTH": 30, "EV-PRO": 30, "EV-ENT": 30, "starter": 30, "growth": 30, "enterprise": 30, "trial": 7, "pro": 30}
PLAN_PRICE = {"Trial": 0, "Starter": 9999, "Growth": 29999, "Pro": 29999, "Enterprise": 79999, "EV-FREE": 0, "EV-STARTER": 9999, "EV-SME": 19999, "EV-GROWTH": 29999, "EV-PRO": 49999, "EV-ENT": 79999, "starter": 9999, "growth": 29999, "enterprise": 79999, "trial": 0, "pro": 29999}
PLAN_PRICES = PLAN_PRICE

class SubscribeRequest(BaseModel):
    plan_name: str
    payment_reference: str = "mpesa_manual"

@router.get("/plans")
def get_plans():
    return {
        "plans": [
            {"name": name, "price_kes": PLAN_PRICE[name], "days": PLAN_DAYS[name], "modules": mods}
            for name, mods in PLAN_MODULES.items()
            if name in ["Trial", "Starter", "Growth", "Pro", "Enterprise"]
        ]
    }

@router.get("/my-subscription")
def my_subscription(db: Session = Depends(get_session), user = Depends(get_current_user)):
    stmt = select(UserSubscription).where(UserSubscription.user_id == user.id, UserSubscription.status == "active")
    subs = db.exec(stmt).all()
    if not subs:
        return {"plan": "Trial", "modules": PLAN_MODULES["Trial"], "expired": True}
    plan_name = subs[0].plan_name
    return {
        "plan": plan_name,
        "modules": [s.module_name for s in subs],
        "expires_at": subs[0].expires_at,
        "all_modules": {k: PLAN_MODULES[k] for k in ["Trial", "Starter", "Growth", "Pro", "Enterprise"] if k in PLAN_MODULES}
    }

@router.post("/subscribe")
def subscribe(
    req: SubscribeRequest,
    db: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    if req.plan_name not in PLAN_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose {list(PLAN_MODULES.keys())}")

    tenant_id = getattr(user, 'tenant_id', user.id)
    expires_at = datetime.now(UTC) + timedelta(days=PLAN_DAYS.get(req.plan_name, 30))

    db.exec(sql_delete(UserSubscription).where(UserSubscription.user_id == user.id))
    db.commit()

    modules_to_add: List[UserSubscription] = []
    for module_name in PLAN_MODULES[req.plan_name]:
        sub = UserSubscription(
            tenant_id=tenant_id,
            user_id=user.id,
            module_name=module_name,
            plan_name=req.plan_name,
            payment_reference=req.payment_reference,
            starts_at=datetime.now(UTC),
            expires_at=expires_at,
            status="active"
        )
        modules_to_add.append(sub)

    db.add_all(modules_to_add)
    db.commit()

    return {
        "status": "success",
        "plan": req.plan_name,
        "modules_activated": PLAN_MODULES[req.plan_name],
        "expires_at": expires_at.isoformat(),
        "tenant_id": tenant_id
    }
