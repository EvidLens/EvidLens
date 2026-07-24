from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from datetime import datetime
from app.modules.auth.models import AuthUser, UserRole
from app.modules.kenyalensiq.models import KenyaLensSubscription
from app.modules.database import get_session as get_db

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.exec(select(AuthUser).where(AuthUser.id == int(user_id))).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user

def require_active_subscription(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    sub = db.exec(select(KenyaSubscription).where(KenyaSubscription.user_id == current_user.id)).first()
    if not sub:
        raise HTTPException(status_code=402, detail="Subscription required")
    if sub.status!= "active":
        raise HTTPException(status_code=402, detail="Subscription not active")
    if sub.expires_at and sub.expires_at < datetime.utcnow():
        raise HTTPException(status_code=402, detail="Subscription expired")
    return current_user

def require_admin(current_user: AuthUser = Depends(get_current_user)):
    if current_user.role!= UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
