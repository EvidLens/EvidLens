from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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
page_router = APIRouter(prefix="/billing", tags=["billing-page"])
templates = Jinja2Templates(directory="app/templates")

PLAN_MODULES = {
    "Trial": ["Core OS", "Market Engine", "Consumer Engine", "AI Insights"],
    "Starter": ["Core OS", "Market Engine", "Consumer Engine"],
    "Growth": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine", "Report Builder", "AI Insights"],
    "Pro": ["Core OS", "Market Engine", "Competitive Engine", "Consumer Engine", "Pricing Engine", "Location Engine", "Report Builder", "AI Insights", "Business OS"],
    "Enterprise": ["Core OS", "Market Engine", "Pricing Engine", "Competitive Engine", "Location Engine", "Consumer Engine", "Regulatory Engine", "Report Builder", "AI Insights", "Business OS", "KenyaLensIQ", "Knowledge Base"],
}

PLAN_DAYS = {"Trial": 7, "Starter": 30, "Growth": 30, "Pro": 30, "Enterprise": 30}
PLAN_PRICE = {"Trial": 0, "Starter": 9999, "Growth": 19999, "Pro": 29999, "Enterprise": 79999}
PLAN_PRICES = PLAN_PRICE

class SubscribeRequest(BaseModel):
    plan_name: str
    payment_reference: str = "mpesa_manual"

@page_router.get("/", response_class=HTMLResponse)
async def billing_page(request: Request, current_user = Depends(get_current_user), db: Session = Depends(get_session)):
    plans_list = []
    for name in ["Trial", "Starter", "Growth", "Pro", "Enterprise"]:
        plans_list.append({
            "name": name,
            "price": PLAN_PRICE.get(name, 0),
            "credits": len(PLAN_MODULES.get(name, [])) * 10,
            "modules": PLAN_MODULES.get(name, []),
            "days": PLAN_DAYS.get(name, 30)
        })
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "current_user": current_user,
        "plans": plans_list
    })

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
    return {
        "plan": subs[0].plan_name,
        "modules": [s.module_name for s in subs],
        "expires_at": subs[0].expires_at,
    }

@router.post("/subscribe")
def subscribe(req: SubscribeRequest, db: Session = Depends(get_session), user = Depends(get_current_user)):
    if req.plan_name not in PLAN_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid plan")
    tenant_id = getattr(user, 'tenant_id', user.id)
    expires_at = datetime.now(UTC) + timedelta(days=PLAN_DAYS.get(req.plan_name, 30))
    db.exec(sql_delete(UserSubscription).where(UserSubscription.user_id == user.id))
    db.commit()
    for module_name in PLAN_MODULES[req.plan_name]:
        db.add(UserSubscription(
            tenant_id=tenant_id, user_id=user.id, module_name=module_name,
            plan_name=req.plan_name, payment_reference=req.payment_reference,
            starts_at=datetime.now(UTC), expires_at=expires_at, status="active"
        ))
    db.commit()
    return {"status": "success", "plan": req.plan_name, "expires_at": expires_at.isoformat()}
