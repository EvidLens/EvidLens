from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from.service import initiate_stk_push, handle_c2b_webhook, verify_payment_status, create_subscription, get_subscription, process_b2c
from.models import Payment, Subscription, PaymentStatus, SubscriptionTier
from app.modules.db import get_db

router = APIRouter()

PAID_REPORTS = {}

class STKPushRequest(BaseModel):
    phone_number: str
    amount: float
    payment_type: str
    reference_id: Optional[str] = None
    description: str

class SubscriptionRequest(BaseModel):
    tier: SubscriptionTier
    phone_number: str
    auto_renew: bool = True

@router.post("/stk-push")
def stk_push(request: STKPushRequest, db: Session = Depends(get_db)):
    result = initiate_stk_push(
        db=db,
        phone_number=request.phone_number,
        amount=request.amount,
        account_reference=request.reference_id or request.description,
        user_id=0
    )
    if result.get("ResponseCode")!= "0":
        raise HTTPException(status_code=400, detail=result.get("errorMessage", "STK Failed"))
    return {"success": True, "checkout_request_id": result.get("CheckoutRequestID"), "data": result}

@router.post("/callback")
async def mpesa_callback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload = await request.json()
    background_tasks.add_task(handle_c2b_webhook, db, payload)
    body = payload.get("Body", {}).get("stkCallback", {})
    if body.get("ResultCode") == 0:
        items = body.get("CallbackMetadata", {}).get("Item", [])
        ref = next((i["Value"] for i in items if i["Name"] == "AccountReference"), None)
        if ref:
            PAID_REPORTS[ref] = {"status": "paid", "data": payload}
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.get("/verify/{checkout_request_id}")
def verify_payment(checkout_request_id: str, db: Session = Depends(get_db)):
    payment = verify_payment_status(db, checkout_request_id)
    if not payment:
        return {"status": "pending"}
    return {
        "status": payment.status.value,
        "amount": payment.amount_kes,
        "mpesa_receipt": payment.mpesa_receipt_number
    }

@router.get("/check/{reference}")
def check_payment(reference: str):
    return PAID_REPORTS.get(reference, {"status": "pending"})

@router.post("/subscribe")
def subscribe(req: SubscriptionRequest, user_id: int, db: Session = Depends(get_db)):
    tier_prices = {
        SubscriptionTier.SME_PRO: 2000,
        SubscriptionTier.PROFESSIONAL: 5000,
        SubscriptionTier.BUSINESS: 15000,
        SubscriptionTier.ENTERPRISE: 40000
    }
    if req.tier == SubscriptionTier.FREE:
        sub = create_subscription(db, user_id, req.tier, auto_renew=False)
        return {"message": "Free tier activated", "subscription": sub}
    amount = tier_prices.get(req.tier, 0)
    stk = initiate_stk_push(
        db=db,
        phone_number=req.phone_number,
        amount=amount,
        account_reference=f"sub_{user_id}",
        user_id=user_id
    )
    return stk

@router.get("/subscription/{user_id}")
def get_user_subscription(user_id: int, db: Session = Depends(get_db)):
    sub = get_subscription(db, user_id)
    return sub

@router.post("/b2c/payout")
def b2c_payout(user_id: int, phone: str, amount: float, reason: str, db: Session = Depends(get_db)):
    result = process_b2c(db, phone, amount, reason)
    return result
