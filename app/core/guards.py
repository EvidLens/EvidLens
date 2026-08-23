from functools import wraps
from fastapi import Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.core.models import UserSubscription
from app.modules.auth.dependencies import get_current_user

# Supports:
# @require_module(1)
# @require_module(module_number=1)
# @require_module("market_intel")
# @require_module(module_name="market_intel")

MODULE_NUMBER_TO_KEY = {
    1: "market_intel",
    2: "competitive_intel",
    3: "consumer_insights",
    4: "pricing_intel",
    5: "regulatory_intel",
    6: "location_intel",
    7: "report_builder",
    8: "ai_insights",
    9: "business_os",
    10: "payments",
    11: "kenyalens_iq",
    12: "knowledge_base",
}

PLAN_MODULES_KEYS = {
    "trial": ["market_intel", "consumer_insights", "ai_insights"],
    "starter": ["market_intel", "consumer_insights"],
    "growth": ["market_intel", "competitive_intel", "consumer_insights", "pricing_intel", "location_intel", "ai_insights", "report_builder"],
    "pro": ["market_intel", "competitive_intel", "consumer_insights", "pricing_intel", "location_intel", "ai_insights", "report_builder", "business_os"],
    "enterprise": ["market_intel", "competitive_intel", "consumer_insights", "pricing_intel", "regulatory_intel", "location_intel", "report_builder", "ai_insights", "business_os", "payments", "kenyalens_iq", "knowledge_base"],
}

EV_TO_PLAN = {
    "EV-FREE": "trial",
    "EV-STARTER": "starter",
    "EV-SME": "growth",
    "EV-GROWTH": "growth",
    "EV-PRO": "pro",
    "EV-ENT": "enterprise",
    "Trial": "trial",
    "Starter": "starter",
    "Growth": "growth",
    "Pro": "pro",
    "Enterprise": "enterprise",
}

def _resolve_key(*args, **kwargs):
    key = None
    if args:
        first = args[0]
        if isinstance(first, int):
            key = MODULE_NUMBER_TO_KEY.get(first)
        elif isinstance(first, str):
            key = first.lower()
    if "module_number" in kwargs:
        key = MODULE_NUMBER_TO_KEY.get(kwargs["module_number"])
    if "module_name" in kwargs:
        key = kwargs["module_name"].lower()
    if "key" in kwargs:
        k = kwargs["key"]
        if isinstance(k, int):
            key = MODULE_NUMBER_TO_KEY.get(k)
        else:
            key = str(k).lower()
    return key

def require_module(*args, **kwargs):
    required_key = _resolve_key(*args, **kwargs) or "market_intel"

    def decorator(func):
        @wraps(func)
        def wrapper(*f_args, **f_kwargs):
            db: Session = f_kwargs.get("db") or (f_args[0] if f_args and isinstance(f_args[0], Session) else None)
            user = f_kwargs.get("user") or f_kwargs.get("current_user")
            # try get db and user from kwargs
            session = f_kwargs.get("db") or f_kwargs.get("session")
            # If called as FastAPI dependency, actual check happens inside
            return func(*f_args, **f_kwargs)
        # FastAPI dependency version
        async def dependency_check(db: Session = Depends(get_session), user = Depends(get_current_user)):
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            # Check UserSubscription for plan
            try:
                stmt = select(UserSubscription).where(UserSubscription.user_id == user.id, UserSubscription.status == "active")
                subs = db.exec(stmt).all()
                if not subs:
                    # allow trial modules
                    if required_key in PLAN_MODULES_KEYS["trial"]:
                        return True
                    raise HTTPException(status_code=403, detail=f"Module {required_key} requires subscription")
                plan_name = subs[0].plan_name
                normalized = EV_TO_PLAN.get(plan_name, plan_name.lower())
                allowed = PLAN_MODULES_KEYS.get(normalized, [])
                # also allow if module_name directly stored
                direct_modules = [s.module_name.lower() for s in subs]
                if required_key in allowed or required_key in direct_modules or "Core OS" in [s.module_name for s in subs]:
                    # Core OS fallback for old naming
                    if required_key in ["market_intel", "consumer_insights"] or any("Core OS" in m for m in [s.module_name for s in subs]):
                        return True
                if required_key in allowed or required_key in direct_modules:
                    return True
                raise HTTPException(status_code=403, detail=f"Plan {plan_name} does not include {required_key}. Upgrade required.")
            except HTTPException:
                raise
            except Exception as e:
                # fail open for dev if table missing
                print(f"Guard check failed open: {e}")
                return True

        wrapper.dependency = dependency_check
        return wrapper
    return decorator

def require_module_key(module_key: str):
    return require_module(module_key)
