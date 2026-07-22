from fastapi import APIRouter, Request, HTTPException
from App.kenyalensiq import services
from App.db import get_session
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/webhooks/payment")
async def payment_webhook(req: Request, session = Depends(get_session)):
    payload = await req.json()
    event = payload.get("event")
    tenant_id = payload.get("tenant_id")
    plan = payload.get("plan") # Pro, Enterprise
    
    if event == "payment.success":
        sub = services.get_subscription(session, tenant_id)
        if not sub:
            sub = LensSubscription(tenant_id=tenant_id)
            
        sub.plan = plan
        sub.modules = ["core","health","money","brand","demand","behavior","policy","capital","trade"]
        sub.expires_at = datetime.utcnow() + timedelta(days=30)
        session.add(sub)
        session.commit()
        return {"status": "upgraded"}
    
    if event == "payment.failed":
        return {"status": "downgraded_to_trial"}
    
    return {"status": "ignored"}
