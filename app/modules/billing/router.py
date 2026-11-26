from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional
import logging

from app.core.db import get_session
from app.core.billing import PLAN_MODULES, PLAN_PRICE, PLAN_DAYS
from app.modules.auth.dependencies import get_current_user, get_current_user_optional
from app.core.models import UserSubscription

router = APIRouter(prefix="/billing", tags=["billing-page"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("evidlens.billing")

PLAN_CREDITS = {
    "Trial": 10,
    "Starter": 100,
    "Growth": 300,
    "Pro": 1000,
    "Enterprise": 5000,
}

PLAN_FEATURES = {
    "Trial": ["1 Report", "Market Prices", "County View", "Community Support"],
    "Starter": ["10 Reports / month", "Market Prices + Demand", "County + Location Intel", "Email Support"],
    "Growth": ["30 Reports / month", "All Market Engines", "Competitive Intel", "Consumer Voice", "Priority Support"],
    "Pro": ["Unlimited Reports", "All 12 Engines", "Report Builder Branded", "Funding + Export", "Priority Support"],
    "Enterprise": ["Everything in Pro", "API Access", "Team Seats (5)", "Dedicated Manager"],
}

PLAN_ORDER = ["Trial", "Starter", "Growth", "Pro", "Enterprise"]

def _get_subscription(db: Session, user_id: int):
    try:
        sub = db.exec(select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.status == "active")).first()
        return sub
    except Exception as e:
        logger.warning(f"subscription lookup failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None

@router.get("/", response_class=HTMLResponse)
async def billing_page(request: Request, current_user=Depends(get_current_user_optional), db: Session = Depends(get_session)):
    plans_list = []
    for name in PLAN_ORDER:
        try:
            price = PLAN_PRICE.get(name, 0) if isinstance(PLAN_PRICE, dict) else 0
            modules = PLAN_MODULES.get(name, []) if isinstance(PLAN_MODULES, dict) else []
            days = PLAN_DAYS.get(name, 30) if isinstance(PLAN_DAYS, dict) else 30
        except Exception:
            price = 0
            modules = []
            days = 30
        plans_list.append({
            "name": name,
            "price": price,
            "price_kes": price,
            "credits": PLAN_CREDITS.get(name, 0),
            "modules": modules,
            "module_count": len(modules),
            "days": days,
            "features": PLAN_FEATURES.get(name, []),
            "is_popular": name == "Pro",
        })

    current_plan = "Trial"
    credits_remaining = 0
    subscription = None
    if current_user is not None and getattr(current_user, "id", None):
        subscription = _get_subscription(db, int(current_user.id))
        if subscription is not None:
            current_plan = str(getattr(subscription, "plan_code", None) or getattr(subscription, "plan", None) or "Trial")
            try:
                credits_remaining = int(getattr(subscription, "credits_remaining", 0) or getattr(subscription, "credits", 0) or 0)
            except Exception:
                credits_remaining = 0

    return templates.TemplateResponse("billing.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "plans": plans_list,
        "current_plan": current_plan,
        "credits_remaining": credits_remaining,
        "subscription": subscription,
        "has_subscription": subscription is not None,
    })

@router.get("/current")
async def current_subscription(current_user=Depends(get_current_user), db: Session = Depends(get_session)):
    sub = _get_subscription(db, int(current_user.id))
    if not sub:
        return {"plan": "Trial", "status": "trial", "credits_remaining": 0, "modules": PLAN_MODULES.get("Trial", [])}
    plan = str(getattr(sub, "plan_code", None) or getattr(sub, "plan", None) or "Trial")
    return {
        "plan": plan,
        "status": getattr(sub, "status", "active"),
        "credits_remaining": int(getattr(sub, "credits_remaining", 0) or getattr(sub, "credits", 0) or 0),
        "modules": PLAN_MODULES.get(plan, []),
        "expires_at": getattr(sub, "expires_at", None),
    }

@router.post("/upgrade/{plan_name}")
async def upgrade_plan(plan_name: str, request: Request, current_user=Depends(get_current_user), db: Session = Depends(get_session)):
    if plan_name not in PLAN_ORDER:
        raise HTTPException(status_code=400, detail="Invalid plan")
    if plan_name == "Trial":
        raise HTTPException(status_code=400, detail="Cannot upgrade to Trial")
    price = PLAN_PRICE.get(plan_name, 0) if isinstance(PLAN_PRICE, dict) else 0
    return {
        "ok": True,
        "plan": plan_name,
        "price_kes": price,
        "credits": PLAN_CREDITS.get(plan_name, 0),
        "message": f"Checkout for {plan_name} KES {price} - complete payment via M-Pesa to activate",
        "next_step": "/billing",
    }
