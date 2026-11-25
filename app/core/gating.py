from fastapi import Depends, HTTPException
from sqlmodel import Session, select, func
from datetime import datetime, timezone
from app.core.db import get_session
from app.core.models import UserSubscription
from app.modules.auth.dependencies import get_current_user

UTC = timezone.utc

PLAN_ORDER = {"FREE": 0, "BASIC": 1, "PROFESSIONAL": 2, "ENTERPRISE": 3}

ALL_MODULES = [
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
]

PLAN_MODULES = {
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
    "ENTERPRISE": ALL_MODULES,
}

# Keep both shapes: analyses/reports/seats for old quota code,
# areas/products/users/competitors/leads for service.py / pricing
PLAN_LIMITS = {
    "FREE": {"analyses": 5, "reports": 1, "seats": 1, "areas": 1, "products": 1, "users": 1, "competitors": 1, "leads_qtr": 0},
    "BASIC": {"analyses": 10, "reports": 5, "seats": 1, "areas": 1, "products": 3, "users": 1, "competitors": 3, "leads_qtr": 0},
    "PROFESSIONAL": {"analyses": 100, "reports": 30, "seats": 1, "areas": 3, "products": 9, "users": 5, "competitors": 10, "leads_qtr": 250},
    "ENTERPRISE": {"analyses": 1000000, "reports": 1000000, "seats": 5, "areas": 9, "products": 21, "users": -1, "competitors": -1, "leads_qtr": -1},
}

FEATURE_TO_MODULE = {
    "demand": "Demand Radar",
    "competitive": "Competitive Engine",
    "pricing": "Price Oracle",
    "location": "County Mapper",
    "consumer": "Consumer Pulse",
    "risk": "Risk Sentinel",
    "policy": "Policy Watch",
    "funding": "Funding Radar",
    "export": "Export Navigator",
    "knowledge": "Knowledge Base",
    "reports": "Report Builder",
    "ai": "AI Insights",
    "alerts": "Risk Sentinel",
    "connectors": "Report Builder",
    "white_label": "Report Builder",
    "team": "Report Builder",
    "api": "Report Builder",
    "market": "Demand Radar",
}

FEATURE_MIN_PLAN = {
    "demand": "FREE",
    "consumer": "FREE",
    "risk": "FREE",
    "export": "FREE",
    "knowledge": "FREE",
    "ai": "FREE",
    "market": "FREE",
    "alerts": "FREE",
    "policy": "BASIC",
    "reports": "BASIC",
    "connectors": "BASIC",
    "competitive": "PROFESSIONAL",
    "pricing": "PROFESSIONAL",
    "location": "PROFESSIONAL",
    "funding": "ENTERPRISE",
    "white_label": "ENTERPRISE",
    "team": "ENTERPRISE",
    "api": "ENTERPRISE",
}

def normalize_plan(name) -> str:
    if not name:
        return "FREE"
    clean = str(name).strip().upper().replace("EV-", "").replace("EV_", "")
    if clean in ("TRIAL",):
        return "FREE"
    if clean in ("STARTER", "SME STARTER", "SME"):
        return "BASIC"
    if clean in ("PRO", "GROWTH", "SME PRO"):
        return "PROFESSIONAL"
    if clean in ("BUSINESS", "ENT"):
        return "ENTERPRISE"
    if clean in PLAN_MODULES:
        return clean
    return "FREE"

def get_active_plan(db: Session, user) -> str:
    stmt = select(UserSubscription).where(
        UserSubscription.user_id == user.id,
        UserSubscription.status == "active",
        UserSubscription.expires_at > datetime.now(UTC),
    )
    sub = db.exec(stmt).first()
    if not sub:
        return "FREE"
    # support both column names: plan_name (yours) and plan_code (other files)
    raw = getattr(sub, "plan_name", None) or getattr(sub, "plan_code", None) or "FREE"
    return normalize_plan(raw)

def get_plan_limits(plan_code) -> dict:
    """What service.py was asking for - was missing before."""
    return dict(PLAN_LIMITS.get(normalize_plan(plan_code), PLAN_LIMITS["FREE"]))

def has_module(plan_code, module_name: str) -> bool:
    return module_name in PLAN_MODULES.get(normalize_plan(plan_code), PLAN_MODULES["FREE"])

def get_credits(db: Session, user) -> int:
    credits = getattr(user, "credits", None)
    if credits is not None:
        return int(credits or 0)
    try:
        from app.modules.wallet.models import Wallet
        wallet = db.exec(select(Wallet).where(Wallet.user_id == user.id)).first()
        if wallet:
            return int(wallet.balance or 0)
    except Exception:
        pass
    return 0

def require_module(module_name: str):
    def dependency(db: Session = Depends(get_session), user=Depends(get_current_user)):
        plan = get_active_plan(db, user)
        allowed = PLAN_MODULES.get(plan, PLAN_MODULES["FREE"])
        if module_name not in allowed:
            raise HTTPException(status_code=403, detail=f"Module '{module_name}' is locked on {plan}. Upgrade to unlock.")
        return user
    return dependency

def require_plan(min_plan: str):
    def dependency(db: Session = Depends(get_session), user=Depends(get_current_user)):
        plan = get_active_plan(db, user)
        if PLAN_ORDER.get(plan, 0) < PLAN_ORDER.get(normalize_plan(min_plan), 0):
            raise HTTPException(status_code=403, detail=f"Requires {normalize_plan(min_plan)} plan or higher. Your plan: {plan}.")
        return user
    return dependency

def require_feature(feature_key: str):
    min_plan = FEATURE_MIN_PLAN.get(feature_key)
    if not min_plan:
        raise ValueError(f"Unknown feature: {feature_key}")
    module = FEATURE_TO_MODULE.get(feature_key, "Report Builder")
    def dependency(db: Session = Depends(get_session), user=Depends(get_current_user)):
        plan = get_active_plan(db, user)
        if PLAN_ORDER.get(plan, 0) < PLAN_ORDER.get(min_plan, 0):
            raise HTTPException(status_code=403, detail=f"Feature '{feature_key}' requires {min_plan} plan or higher. Your plan: {plan}.")
        allowed = PLAN_MODULES.get(plan, PLAN_MODULES["FREE"])
        if module not in allowed:
            raise HTTPException(status_code=403, detail=f"Feature '{feature_key}' is locked. Upgrade to unlock.")
        return user
    return dependency

def check_quota(db: Session, user, quota_type: str) -> bool:
    plan = get_active_plan(db, user)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["FREE"])
    if quota_type not in limits:
        return True
    max_allowed = limits[quota_type]
    if max_allowed >= 1000000:
        return True
    if quota_type in ("analyses", "reports"):
        try:
            from app.modules.report_builder.models import Report
            current = db.exec(select(func.count(Report.id)).where(Report.user_id == user.id)).one() or 0
        except Exception:
            current = 0
    elif quota_type == "seats":
        current = db.exec(select(func.count(func.distinct(UserSubscription.user_id))).where(UserSubscription.user_id == user.id)).one() or 1
        if current > max_allowed:
            raise HTTPException(status_code=402, detail=f"Seats limit {max_allowed} reached on {plan}. Upgrade.")
        return True
    else:
        return True
    if current >= max_allowed:
        raise HTTPException(status_code=402, detail=f"{quota_type} limit {max_allowed} reached on {plan}. Buy credits or upgrade.")
    return True

def require_credits(amount: int = 1):
    def dependency(db: Session = Depends(get_session), user=Depends(get_current_user)):
        credits = get_credits(db, user)
        if credits < amount:
            raise HTTPException(status_code=402, detail=f"Not enough credits. You have {credits}, need {amount}. Buy credits or upgrade.")
        return user
    return dependency

def consume_credits(db: Session, user, amount: int = 1) -> int:
    credits = get_credits(db, user)
    if credits < amount:
        raise HTTPException(status_code=402, detail=f"Not enough credits. You have {credits}, need {amount}. Buy credits or upgrade.")
    new_balance = credits - amount
    if hasattr(user, "credits"):
        user.credits = new_balance
        db.add(user)
        db.commit()
        return new_balance
    try:
        from app.modules.wallet.models import Wallet
        wallet = db.exec(select(Wallet).where(Wallet.user_id == user.id)).first()
        if wallet:
            wallet.balance = new_balance
            db.add(wallet)
            db.commit()
            return new_balance
    except Exception:
        pass
    return new_balance
