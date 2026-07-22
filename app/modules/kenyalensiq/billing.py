from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session
from App.kenyalensiq import services
from App.kenyalensiq.models import Subscription
from App.db import get_session
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/webhooks/payment")
async def payment_webhook(req: Request, session: Session = Depends(get_session)):
    payload = await req.json()
    event = payload.get("event")
    tenant_id = payload.get("tenant_id")
    plan = payload.get("plan")

    if not tenant_id:
        raise HTTPException(400, "tenant_id required")

    if event == "payment.success":
        sub = services.get_subscription(session, tenant_id) or Subscription(tenant_id=tenant_id)
            
        sub.plan = plan
        sub.modules = ["core","health","money","brand","demand","behavior","policy","capital","trade"]
        days = 30 if plan == "Pro" else 365
        sub.expires_at = datetime.utcnow() + timedelta(days=days)
        session.add(sub)
        session.commit()
        services.log_audit(session, tenant_id, "system", "payment_success", "billing", {"plan": plan})
        return {"status": "upgraded"}

    if event == "payment.failed":
        sub = services.get_subscription(session, tenant_id)
        if sub:
            sub.plan = "Trial"
            sub.modules = ["core","health"]
            sub.expires_at = datetime.utcnow() + timedelta(days=7)
            session.add(sub)
            session.commit()
        services.log_audit(session, tenant_id, "system", "payment_failed", "billing")
        return {"status": "downgraded_to_trial"}
    
    return {"status": "ignored"}
