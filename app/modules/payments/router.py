from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from.service import (
    initiate_stk_push,
    handle_c2b_webhook,
    verify_payment,
    create_subscription,
    get_subscription
)
from.models import Payment, Subscription, PaymentStatus, SubscriptionTier
from app.modules.database import get_db

router = APIRouter()

class STKPushRequest(BaseModel):
    phone_number: str
    amount: float
    payment_type: str
    reference_id: Optional[int] = None
    description: str

class SubscriptionRequest(BaseModel):
    tier: SubscriptionTier
    phone_number: str
    auto_renew: bool = True

@router.post("/stk-push")
def stk_push(request: STKPushRequest, db: Session = Depends(get_db)):
    """Initiate M-Pesa STK Push. Used for SME Starter, Pro, Enterprise + Pay-Per-Report"""
    result = initiate_stk_push(
        db=db,
        phone=request.phone_number,
        amount=request.amount,
        payment_type=request.payment_type,
        reference_id=request.reference_id,
        description=request.description
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/callback")
async def mpesa_callback(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Safaricom Daraja callback URL. Handles STK success/failure"""
    payload = await request.json()
    background_tasks.add_task(handle_c2b_webhook, db, payload)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.get("/verify/{checkout_request_id}")
def verify_payment(checkout_request_id: str, db: Session = Depends(get_db)):
    """Check payment status. Poll from frontend after STK Push"""
    payment = verify_payment_status(db, checkout_request_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "status": payment.status,
        "amount": payment.amount_kes,
        "mpesa_receipt": payment.mpesa_receipt_number
    }

@router.post("/subscribe")
def subscribe(req: SubscriptionRequest, user_id: int, db: Session = Depends(get_db)):
    """Create/upgrade subscription. Triggers STK Push for paid tiers"""
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
        phone=req.phone_number,
        amount=amount,
        payment_type="subscription",
        description=f"EvidLens {req.tier.value} subscription"
    )
    return stk

@router.get("/subscription/{user_id}")
def get_user_subscription(user_id: int, db: Session = Depends(get_db)):
    """Get current subscription + limits. Powers Profile Page"""
    sub = get_subscription(db, user_id)
    return sub

@router.post("/b2c/payout")
def b2c_payout(user_id: int, phone: str, amount: float, reason: str, db: Session = Depends(get_db)):
    """B2C for refunds and 'Referral: Get 1 free report'"""
    from.service import process_b2c
    result = process_b2c(db, user_id, phone, amount, reason)
    return result
