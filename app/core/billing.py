from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from sqlmodel import delete as sql_delete
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.core.db import get_session
from app.core.models import UserSubscription
from app.modules.auth.dependencies import get_current_user

UTC = timezone.utc
router = APIRouter(prefix="/api/billing", tags=["billing"])
page_router = APIRouter(prefix="/billing", tags=["billing-page"])
templates = Jinja2Templates(directory="app/templates")

ALL_MODULES = [
    "Demand Lens",
    "Competitive Lens",
    "Risk Sentinel",
    "Market Intelligence",
    "Policy Watch",
    "Report Builder",
]

PLAN_MODULES = {
    "FREE": [],
    "BASIC": ALL_MODULES,
    "PROFESSIONAL": ALL_MODULES,
    "ENTERPRISE": ALL_MODULES,
}

PLAN_LIMITS = {
    "FREE": {"analyses": 5, "reports": 1, "seats": 1},
    "BASIC": {"analyses": 10, "reports": 5, "seats": 1},
    "PROFESSIONAL": {"analyses": 100, "reports": 30, "seats": 1},
    "ENTERPRISE": {"analyses": 1000000, "reports": 1000000, "seats": 5},
}

PLAN_DAYS = {"FREE": 0, "BASIC": 30, "PROFESSIONAL": 30, "ENTERPRISE": 30}

PLAN_PRICE = {"FREE": 0, "BASIC": 500, "PROFESSIONAL": 1500, "ENTERPRISE": 5000}

PLAN_YEARLY_PRICE = {"FREE": 0, "BASIC": 5000, "PROFESSIONAL": 15000, "ENTERPRISE": 50000}

PLAN_PRICES = PLAN_PRICE

PLAN_NAMES = ["FREE", "BASIC", "PROFESSIONAL", "ENTERPRISE"]

def normalize_plan(name: Optional[str]) -> str:
    if not name:
        return "FREE"
    clean = str(name).strip().upper().replace("EV-", "").replace("EV_", "")
    if clean in ("SME STARTER", "STARTER"):
        return "BASIC"
    if clean in ("SME PRO", "PRO", "GROWTH"):
        return "PROFESSIONAL"
    if clean in ("BUSINESS",):
        return "ENTERPRISE"
    if clean in PLAN_MODULES:
        return clean
    return "FREE"

def plan_payload(name: str, billing: str = "monthly") -> dict:
    norm = normalize_plan(name)
    price = PLAN_YEARLY_PRICE[norm] if billing == "yearly" else PLAN_PRICE[norm]
    return {
        "name": norm,
        "price_kes": price,
        "price": price,
        "billing": billing,
        "days": 365 if billing == "yearly" else PLAN_DAYS[norm],
        "modules": PLAN_MODULES[norm],
        "limits": PLAN_LIMITS[norm],
    }

class SubscribeRequest(BaseModel):
    plan_name: str
    billing: str = "monthly"
    payment_reference: Optional[str] = None
    checkout_request_id: Optional[str] = None

@page_router.get("/", response_class=HTMLResponse)
async def billing_page(request: Request, current_user=Depends(get_current_user), db: Session = Depends(get_session)):
    plans_list = [plan_payload(name, "monthly") for name in PLAN_NAMES]
    plans_list_yearly = [plan_payload(name, "yearly") for name in PLAN_NAMES]
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "current_user": current_user,
        "plans": plans_list,
        "plans_yearly": plans_list_yearly,
    })

@router.get("/plans")
def get_plans():
    return {
        "plans": [plan_payload(name, "monthly") for name in PLAN_NAMES],
        "plans_yearly": [plan_payload(name, "yearly") for name in PLAN_NAMES],
    }

@router.get("/my-subscription")
def my_subscription(db: Session = Depends(get_session), user=Depends(get_current_user)):
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == user.id,
        UserSubscription.status == "active",
    )
    subs = db.exec(stmt).all()
    if not subs:
        return {"plan": "FREE", "modules": [], "limits": PLAN_LIMITS["FREE"], "expired": True}
    plan = normalize_plan(subs[0].plan_name)
    return {
        "plan": plan,
        "modules": PLAN_MODULES[plan],
        "limits": PLAN_LIMITS[plan],
        "expires_at": subs[0].expires_at,
        "expired": bool(subs[0].expires_at and subs[0].expires_at < datetime.now(UTC)),
    }

@router.post("/subscribe")
def subscribe(req: SubscribeRequest, db: Session = Depends(get_session), user=Depends(get_current_user)):
    plan = normalize_plan(req.plan_name)
    if plan == "FREE":
        raise HTTPException(status_code=400, detail="FREE plan needs no subscription. Use credits or upgrade.")
    billing = req.billing.lower() if req.billing else "monthly"
    if billing not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="billing must be monthly or yearly")
    if not req.checkout_request_id and not req.payment_reference:
        raise HTTPException(status_code=402, detail="Payment required. Complete M-Pesa STK Push first, then retry with checkout_request_id.")
    try:
        from app.modules.wallet.models import PaymentTransaction
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.checkout_request_id == req.checkout_request_id if req.checkout_request_id else PaymentTransaction.receipt_number == req.payment_reference,
        )
        tx = db.exec(stmt).first()
        if not tx or str(getattr(tx, "status", "")).upper() not in ("COMPLETED", "SUCCESS", "PAID"):
            raise HTTPException(status_code=402, detail="Payment not verified. Wait for M-Pesa confirmation, then retry.")
        expected = PLAN_YEARLY_PRICE[plan] if billing == "yearly" else PLAN_PRICE[plan]
        if int(getattr(tx, "amount", 0) or 0) < expected:
            raise HTTPException(status_code=402, detail=f"Payment amount too low for {plan} {billing}. Expected KES {expected}.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=402, detail="Payment verification unavailable. Try again in a minute.")
    tenant_id = getattr(user, "tenant_id", user.id)
    days = 365 if billing == "yearly" else PLAN_DAYS.get(plan, 30)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=days)
    db.exec(sql_delete(UserSubscription).where(UserSubscription.user_id == user.id))
    db.commit()
    for module_name in PLAN_MODULES[plan]:
        db.add(UserSubscription(
            tenant_id=tenant_id,
            user_id=user.id,
            module_name=module_name,
            plan_name=plan,
            payment_reference=req.payment_reference or req.checkout_request_id or "",
            starts_at=now,
            expires_at=expires_at,
            status="active",
        ))
    db.commit()
    return {"status": "success", "plan": plan, "billing": billing, "expires_at": expires_at.isoformat()}
