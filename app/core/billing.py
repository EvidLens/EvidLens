from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, delete
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

class SubscribeRequest(BaseModel):
    plan_name: str
    payment_reference: str

@router.post("/subscribe")
async def subscribe(
    req: SubscribeRequest,
    db: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    if req.plan_name not in PLAN_MODULES:
        raise HTTPException(status_code=400, detail="Invalid plan")

    tenant_id = user.tenant_id
    expires_at = datetime.now(UTC) + timedelta(days=PLAN_DAYS[req.plan_name])

    db.exec(delete(UserSubscription).where(UserSubscription.tenant_id == tenant_id))

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
