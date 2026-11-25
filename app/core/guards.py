from fastapi import Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timezone
from app.core.db import get_session
from app.core.models import UserSubscription
from app.modules.auth.dependencies import get_current_user

UTC = timezone.utc

MODULE_NUMBER_TO_KEY = {
    1: "Competitive Engine",
    2: "Price Oracle",
    3: "Demand Radar",
    4: "County Mapper",
    5: "Consumer Pulse",
    6: "Risk Sentinel",
    7: "Policy Watch",
    8: "Funding Radar",
    9: "Export Navigator",
    10: "Knowledge Base",
    11: "Report Builder",
    12: "AI Insights",
}

KEY_TO_MODULE = {
    "competitive_engine": "Competitive Engine",
    "competitive_intel": "Competitive Engine",
    "price_oracle": "Price Oracle",
    "pricing_intel": "Price Oracle",
    "demand_radar": "Demand Radar",
    "market_intel": "Demand Radar",
    "county_mapper": "County Mapper",
    "location_intel": "County Mapper",
    "consumer_pulse": "Consumer Pulse",
    "consumer_insights": "Consumer Pulse",
    "risk_sentinel": "Risk Sentinel",
    "regulatory_intel": "Risk Sentinel",
    "policy_watch": "Policy Watch",
    "funding_radar": "Funding Radar",
    "export_navigator": "Export Navigator",
    "knowledge_base": "Knowledge Base",
    "report_builder": "Report Builder",
    "ai_insights": "AI Insights",
    "business_os": "Funding Radar",
}

PLAN_MODULES_KEYS = {
    "FREE": [
        "Demand Radar",
        "Consumer Pulse",
        "Risk Sentinel",
        "Export Navigator",
        "Knowledge Base",
        "AI Insights",
    ],
    "BASIC": [
        "Demand Radar",
        "Consumer Pulse",
        "Risk Sentinel",
        "Export Navigator",
        "Knowledge Base",
        "AI Insights",
        "Policy Watch",
        "Report Builder",
    ],
    "PROFESSIONAL": [
        "Demand Radar",
        "Consumer Pulse",
        "Risk Sentinel",
        "Export Navigator",
        "Knowledge Base",
        "AI Insights",
        "Policy Watch",
        "Report Builder",
        "Competitive Engine",
        "Price Oracle",
        "County Mapper",
    ],
    "ENTERPRISE": [
        "Competitive Engine",
        "Price Oracle",
        "Demand Radar",
        "County Mapper",
        "Consumer Pulse",
        "Risk Sentinel",
        "Policy Watch",
        "Funding Radar",
        "Export Navigator",
        "Knowledge Base",
        "Report Builder",
        "AI Insights",
    ],
}

EV_TO_PLAN = {
    "EV-FREE": "FREE",
    "EV-STARTER": "BASIC",
    "EV-SME": "PROFESSIONAL",
    "EV-GROWTH": "PROFESSIONAL",
    "EV-PRO": "PROFESSIONAL",
    "EV-ENT": "ENTERPRISE",
    "EV-ENTERPRISE": "ENTERPRISE",
    "TRIAL": "FREE",
    "STARTER": "BASIC",
    "GROWTH": "PROFESSIONAL",
    "PRO": "PROFESSIONAL",
    "ENTERPRISE": "ENTERPRISE",
    "FREE": "FREE",
    "BASIC": "BASIC",
    "PROFESSIONAL": "PROFESSIONAL",
}

def normalize_plan(name) -> str:
    if not name:
        return "FREE"
    clean = str(name).strip().upper().replace("EV-", "EV_").replace("EV_", "EV-")
    if clean in EV_TO_PLAN:
        return EV_TO_PLAN[clean]
    key = str(name).strip().upper()
    if key in EV_TO_PLAN:
        return EV_TO_PLAN[key]
    if key in PLAN_MODULES_KEYS:
        return key
    return "FREE"

def resolve_module(*args, **kwargs) -> str:
    if args:
        first = args[0]
        if isinstance(first, int):
            return MODULE_NUMBER_TO_KEY.get(first, "Demand Radar")
        if isinstance(first, str):
            low = first.strip().lower()
            if low in KEY_TO_MODULE:
                return KEY_TO_MODULE[low]
            return first
    if "module_number" in kwargs:
        return MODULE_NUMBER_TO_KEY.get(kwargs["module_number"], "Demand Radar")
    if "module_name" in kwargs:
        name = str(kwargs["module_name"])
        low = name.strip().lower()
        if low in KEY_TO_MODULE:
            return KEY_TO_MODULE[low]
        return name
    if "key" in kwargs:
        k = kwargs["key"]
        if isinstance(k, int):
            return MODULE_NUMBER_TO_KEY.get(k, "Demand Radar")
        low = str(k).strip().lower()
        if low in KEY_TO_MODULE:
            return KEY_TO_MODULE[low]
        return str(k)
    return "Demand Radar"

def _resolve_key(*args, **kwargs) -> str:
    return resolve_module(*args, **kwargs)

def get_active_plan(db: Session, user) -> str:
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == user.id,
        UserSubscription.status == "active",
        UserSubscription.expires_at > datetime.now(UTC),
    )
    sub = db.exec(stmt).first()
    if not sub:
        return "FREE"
    return normalize_plan(sub.plan_name)

def require_module(*args, **kwargs):
    required_module = resolve_module(*args, **kwargs)
    def dependency(db: Session = Depends(get_session), user=Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        plan = get_active_plan(db, user)
        allowed = PLAN_MODULES_KEYS.get(plan, PLAN_MODULES_KEYS["FREE"])
        if required_module in allowed:
            return user
        raise HTTPException(status_code=403, detail=f"Module '{required_module}' is locked on {plan}. Upgrade to unlock.")
    return dependency

def require_module_key(module_key: str):
    return require_module(module_key)

def consume_credits(amount: int = 1):
    def dependency(db: Session = Depends(get_session), user=Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        credits = getattr(user, "credits", None)
        if credits is None:
            try:
                from app.modules.wallet.models import Wallet
                wallet = db.exec(select(Wallet).where(Wallet.user_id == user.id)).first()
                credits = int(wallet.balance or 0) if wallet else 0
            except Exception:
                credits = 0
        else:
            credits = int(credits or 0)
        if credits < amount:
            raise HTTPException(status_code=402, detail=f"Not enough credits. You have {credits}, need {amount}. Buy credits or upgrade.")
        new_balance = credits - amount
        if hasattr(user, "credits"):
            user.credits = new_balance
            db.add(user)
            db.commit()
        else:
            try:
                from app.modules.wallet.models import Wallet
                wallet = db.exec(select(Wallet).where(Wallet.user_id == user.id)).first()
                if wallet:
                    wallet.balance = new_balance
                    db.add(wallet)
                    db.commit()
            except Exception:
                pass
        return user
    return dependency
