from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session
from app.modules.kenyalensiq.models import KenyaLensSubscription
from app.modules.kenyalensiq import services
from app.core.db import get_session
from datetime import datetime, timezone, timedelta
import json

UTC = timezone.utc
router = APIRouter()

@router.post("/webhooks/mpesa")
async def mpesa_callback(req: Request, session: Session = Depends(get_session)):
    body = await req.json()
    callback = body.get("Body", {}).get("stkCallback", {})
    
    if callback.get("ResultCode") != 0:
        return {"ResultCode": 0}
        
    items = {i["Name"]: i["Value"] for i in callback["CallbackMetadata"]["Item"]}
    user_id = int(items["AccountReference"])
    receipt = items["MpesaReceiptNumber"]
    amount = items["Amount"]

    sub = services.get_subscription(session, user_id)
    if sub:
        metadata = json.loads(sub.metadata_json or '{}')
        if metadata.get("last_payment") == receipt:
            return {"ResultCode": 0, "ResultDesc": "Already processed"}

    sub = sub or KenyaLensSubscription(user_id=user_id)
    
    if amount >= 50000:
        sub.plan_code = "EV-ENT"
        days = 365
        credits = 5000
        leads = 1000
    else:
        sub.plan_code = "EV-PRO"
        days = 30
        credits = 1000
        leads = 250

    sub.status = "active"
    sub.renews_at = datetime.now(UTC) + timedelta(days=days)
    sub.api_credits = credits
    sub.lead_credits = leads
    sub.features_json = json.dumps(["core","health","money","brand","demand","behavior","policy","capital","trade"])
    
    metadata = json.loads(sub.metadata_json or '{}')
    metadata["last_payment"] = receipt
    metadata["last_phone"] = items["PhoneNumber"]
    metadata["last_amount"] = amount
    sub.metadata_json = json.dumps(metadata)

    session.add(sub)
    session.commit()
    services.log_audit(session, user_id, user_id, "mpesa_payment", "billing", {"receipt": receipt, "amount": amount})
    return {"ResultCode": 0, "ResultDesc": "Success"}
