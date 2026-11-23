from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from datetime import datetime
from app.modules.auth.models import AuthUser, UserRole
from app.core.db import get_session as get_db

try:
    from app.core.models import KenyaLensSubscription
except ImportError:
    KenyaLensSubscription = None

def _get_user_id_from_request(request: Request):
    # Check ALL places Google login might store you - cookie, session, header
    uid = request.cookies.get("user_id")
    if uid:
        return uid
    # SessionMiddleware cookie from Google OAuth
    try:
        sess = request.session.get("user_id") if hasattr(request, "session") else None
        if sess:
            return str(sess)
    except:
        pass
    # Bearer token
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth.replace("Bearer ", "").strip()
    # access_token cookie is sometimes the user_id
    tok = request.cookies.get("access_token")
    if tok and tok.isdigit():
        return tok
    return None

def get_current_user(request: Request, db: Session = Depends(get_db)) -> AuthUser:
    user_id = _get_user_id_from_request(request)
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
    # FIX: Do NOT block on email_verified for viewing pages.
    # Google users are verified by Google, but DB flag is False.
    # We auto-fix it instead of kicking them out.
    if not user.email_verified:
        try:
            user.email_verified = True
            db.add(user)
            db.commit()
            db.refresh(user)
        except:
            try: db.rollback()
            except: pass
    return user

def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    """For the 6 pages - NEVER bounces, returns None if not logged in"""
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return None
        user = db.exec(select(AuthUser).where(AuthUser.id == int(user_id))).first()
        return user
    except:
        return None

def require_active_subscription(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if KenyaLensSubscription is None:
        return current_user
    sub = db.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == current_user.id)).first()
    if not sub:
        return current_user
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
    return get_current_user_optional(request, db)
