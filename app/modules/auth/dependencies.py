from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from datetime import datetime
from app.modules.auth.models import AuthUser, UserRole
from app.core.db import get_session as get_db

# Safe import - if KenyaLensSubscription deleted, skip check
try:
    from app.core.models import KenyaLensSubscription
except ImportError:
    KenyaLensSubscription = None

def get_current_user(request: Request, db: Session = Depends(get_db)) -> AuthUser:
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        uid = int(user_id)
    except:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user = db.exec(select(AuthUser).where(AuthUser.id == uid)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    # Security: require verified email for all protected routes
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    return user

def require_active_subscription(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if KenyaLensSubscription is None:
        return current_user
    sub = db.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == current_user.id)).first()
    if not sub:
        return current_user # allow if no sub record (free tier)
    if sub.status != "active":
        raise HTTPException(status_code=402, detail="Subscription not active")
    if sub.expires_at and sub.expires_at < datetime.utcnow():
        raise HTTPException(status_code=402, detail="Subscription expired")
    return current_user

def require_admin(current_user: AuthUser = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """For public pages - returns None if not logged in"""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        return db.exec(select(AuthUser).where(AuthUser.id == int(user_id))).first()
    except:
        return None
