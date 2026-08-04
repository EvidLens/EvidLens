from fastapi import Depends, HTTPException
from sqlmodel import Session, select, func
from app.modules.core.service import check_access
from app.modules.auth.models import AuthUser
from app.modules.core.models import KenyaLensBusiness
from app.modules.market_engine.models import MarketMetric
from app.core.db import get_session
from app.modules.auth.dependencies import get_current_user

def get_limits(db: Session, user_id: int):
    access = check_access(db, user_id, "")
    return access["plan"], access["limits"]

def require_feature(feature: str):
    def decorator(func):
        async def wrapper(*args, db: Session = Depends(get_session), current_user: AuthUser = Depends(get_current_user), **kwargs):
            plan, limits = get_limits(db, current_user.id)
            if feature == "api" and not limits.get("api"): 
                raise HTTPException(403, f"API requires ENTERPRISE. You: {plan}")
            if feature == "pro_lens" and limits["lens"] not in ["Pro", "Enterprise"]: 
                raise HTTPException(403, f"Pro Lens requires GROWTH+. You: {plan}")
            if feature == "no_watermark" and limits.get("watermark"): 
                raise HTTPException(403, f"No Watermark requires SME+. You: {plan}")
            if feature == "weekly_briefings" and not limits.get("briefings"): 
                raise HTTPException(403, f"Weekly requires ENTERPRISE. You: {plan}")
            return await func(*args, db=db, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def check_quota(db: Session, user_id: int, quota_type: str):
    plan, limits = get_limits(db, user_id)
    max_allowed = limits.get(quota_type)
    
    if quota_type == "products": 
        current = db.exec(select(func.count(func.distinct(MarketMetric.product)))).one() or 0
    elif quota_type == "areas": 
        current = db.exec(select(func.count(func.distinct(MarketMetric.county)))).one() or 0
    elif quota_type == "competitors": 
        current = db.exec(select(func.count(func.distinct(KenyaLensBusiness.id)))).one() or 0
    elif quota_type == "users": 
        current = 1
    elif quota_type == "leads_qtr": 
        current = 0
    else: 
        return True
    
    if max_allowed == -1: return True
    if current >= max_allowed: 
        raise HTTPException(402, f"{quota_type} limit {max_allowed} reached on {plan}. Upgrade.")
    return True
