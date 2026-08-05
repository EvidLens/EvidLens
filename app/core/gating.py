from fastapi import Depends, HTTPException
from sqlmodel import Session, select, func
from datetime import datetime, timezone
from typing import Callable

from app.core.db import get_session
from app.core.models import UserSubscription, KenyaLensBusiness, MarketMetric
from app.core.auth import get_current_user

UTC = timezone.utc

def require_module(module_name: str):
    def decorator(func: Callable):
        async def wrapper(*args, db: Session = Depends(get_session), user = Depends(get_current_user), **kwargs):
            tenant_id = user.tenant_id
            
            sub = db.exec(
                select(UserSubscription).where(
                    UserSubscription.tenant_id == tenant_id,
                    UserSubscription.module_name == module_name,
                    UserSubscription.status == "active",
                    UserSubscription.expires_at > datetime.now(UTC)
                )
            ).first()
            
            if not sub:
                raise HTTPException(status_code=403, detail=f"Module '{module_name}' is locked. Upgrade to unlock.")
                
            return await func(*args, db=db, user=user, **kwargs)
        return wrapper
    return decorator

def require_feature(feature_key: str):
    FEATURE_TO_MODULE = {
        "alerts": "AI Insights",
        "connectors": "Report Builder",
        "white_label": "KenyaLensIQ",
        "team": "Report Builder",
        "api": "KenyaLensIQ"
    }
    required_module = FEATURE_TO_MODULE.get(feature_key)
    if not required_module:
        raise ValueError(f"Unknown feature: {feature_key}")
    return require_module(required_module)

def check_quota(db: Session, user: any, quota_type: str):
    tenant_id = user.tenant_id
    
    plan_sub = db.exec(
        select(UserSubscription).where(
            UserSubscription.tenant_id == tenant_id,
            UserSubscription.status == "active"
        )
    ).first()
    
    if not plan_sub:
        raise HTTPException(status_code=402, detail="No active subscription")
    
    plan = plan_sub.plan_name
    
    LIMITS = {
        "Trial": {"users": 1, "api": 10, "widgets": 0},
        "Pro": {"users": 5, "api": 100, "widgets": 1},
        "Enterprise": {"users": -1, "api": 1000, "widgets": -1}
    }
    
    max_allowed = LIMITS.get(plan, {}).get(quota_type)
    if max_allowed is None:
        return True
    if max_allowed == -1:
        return True
        
    if quota_type == "products": 
        current = db.exec(select(func.count(func.distinct(MarketMetric.product)))).one() or 0
    elif quota_type == "areas": 
        current = db.exec(select(func.count(func.distinct(MarketMetric.county)))).one() or 0
    elif quota_type == "competitors": 
        current = db.exec(select(func.count(func.distinct(KenyaLensBusiness.id)))).one() or 0
    elif quota_type == "users": 
        current = db.exec(select(func.count(func.distinct(UserSubscription.user_id))).where(UserSubscription.tenant_id == tenant_id)).one() or 0
    else: 
        return True
    
    if current >= max_allowed: 
        raise HTTPException(status_code=402, detail=f"{quota_type} limit {max_allowed} reached on {plan}. Upgrade.")
    return True
