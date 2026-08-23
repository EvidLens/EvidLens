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
    "Trial": ["Core OS", "Market Engine", "Consumer Engine"],
    "Pro": ["Core OS", "Market Engine", "Pricing Engine", "Competitive Engine", "Location Engine", "Consumer Engine", "Report Builder", "AI Insights"],
    "Enterprise": ["Core OS", "Market Engine", "Pricing Engine", "Competitive Engine", "Location Engine", "Consumer Engine", "Regulatory Engine", "Report Builder", "AI Insights", "Business OS"]
}

PLAN_DAYS = {"Trial": 7, "Pro": 30, "Enterprise": 30}
PLAN_PRICE = {"Trial": 0, "Pro": 5000, "Enterprise": 20000}

class SubscribeRequest(BaseModel):
    plan_name: str
    payment_reference: str = "mpesa_manual"

@router.get("/plans")
def get_plans():
    return {
        "plans": [
            {"name": name, "price_kes": PLAN_PRICE[name], "days": PLAN_DAYS[name], "modules": mods}
            for name, mods in PLAN_MODULES.items()
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
        "all_modules": PLAN_MODULES
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
    expires_at = datetime.now(UTC) + timedelta(days=PLAN_DAYS[req.plan_name])

    # Remove old active subs for this tenant/user
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
