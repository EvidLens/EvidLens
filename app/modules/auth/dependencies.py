from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select
from datetime import datetime, timezone
from app.modules.auth.models import AuthUser, UserRole
from app.core.db import get_session as get_db

try:
    from app.core.models import KenyaLensSubscription
except ImportError:
    KenyaLensSubscription = None

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _get_user_id_from_request(request: Request):
    # 1. Starlette session
    try:
        sess = request.session.get("user_id") if hasattr(request, "session") else None
        if sess:
            return str(sess)
    except Exception:
        pass
    # 2. COOKIES - THIS WAS MISSING. This is what login actually sets.
    for key in ("user_id", "session", "auth_user_id"):
        try:
            v = request.cookies.get(key)
            if v and str(v).isdigit():
                return str(v)
        except Exception:
            continue
    # 3. Bearer header
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.replace("Bearer ", "").strip()
        if token.isdigit():
            return token
    return None

def get_current_user(request: Request, db: Session = Depends(get_db)) -> AuthUser:
    user_id = _get_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        uid = int(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = db.exec(select(AuthUser).where(AuthUser.id == uid)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user

def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    try:
        user_id = _get_user_id_from_request(request)
        if not user_id:
            return None
        try:
            uid = int(user_id)
        except Exception:
            return None
        user = db.exec(select(AuthUser).where(AuthUser.id == uid)).first()
        if user and not user.is_active:
            return None
        return user
    except Exception:
        return None

def require_active_subscription(current_user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if KenyaLensSubscription is None:
        return current_user
    sub = db.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == current_user.id)).first()
    if not sub:
        return current_user
    if sub.status != "active":
        raise HTTPException(status_code=402, detail="Subscription not active")
    if sub.expires_at and sub.expires_at < _utcnow():
        raise HTTPException(status_code=402, detail="Subscription expired")
    return current_user

def require_admin(current_user: AuthUser = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def get_optional_user(request: Request, db: Session = Depends(get_db)):
    return get_current_user_optional(request, db)
