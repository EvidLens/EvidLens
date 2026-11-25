import os
import time
import secrets
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlmodel import Session, select
from app.core.db import get_session as get_db
from app.modules.auth.models import AuthUser, UserRole

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60

ACTIVE_PLANS = {"basic", "professional", "enterprise", "free"}
PAID_PLANS = {"basic", "professional", "enterprise"}
PLAN_RANK = {"free": 0, "basic": 1, "professional": 2, "enterprise": 3}

def create_access_token(user_id: int, email: str = "") -> str:
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set")
    now = int(time.time())
    payload = {"sub": str(user_id), "email": email, "iat": now, "exp": now + ACCESS_TOKEN_EXPIRE_SECONDS, "jti": secrets.token_hex(8)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    if not token or not SECRET_KEY:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return int(user_id)
    except (JWTError, ValueError, TypeError):
        return None

def get_user_by_id(db: Session, user_id: int):
    if not user_id:
        return None
    try:
        return db.exec(select(AuthUser).where(AuthUser.id == int(user_id))).first()
    except (ValueError, TypeError):
        return None

def _unauthorized():
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required.", headers={"WWW-Authenticate": "Bearer"})

def _forbidden(detail: str = "Access denied."):
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

def get_current_user_from_request(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)):
    user = None
    if credentials and credentials.credentials:
        user_id = decode_access_token(credentials.credentials)
        if user_id:
            user = get_user_by_id(db, user_id)
    if user is None:
        cookie_id = request.cookies.get("user_id")
        if cookie_id:
            try:
                user = get_user_by_id(db, int(cookie_id))
            except (ValueError, TypeError):
                user = None
    if user is None:
        raise _unauthorized()
    if not getattr(user, "is_active", True):
        raise _forbidden("Account is deactivated. Contact support@evidlens.co.ke")
    return user

def require_active_subscription(credentials: HTTPAuthorizationCredentials | None = Depends(security), request: Request = None, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, credentials, db)
    plan = str(getattr(user, "plan", "free") or "free").lower()
    if plan not in ACTIVE_PLANS:
        raise _forbidden("No active subscription. Upgrade to continue.")
    if plan == "free":
        credits = getattr(user, "credits", 0) or 0
        if credits <= 0:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Out of free credits. Buy credits or upgrade to continue.")
    return user

def require_paid_plan(user: AuthUser = Depends(get_current_user_from_request)):
    plan = str(getattr(user, "plan", "free") or "free").lower()
    if plan not in PAID_PLANS:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="This feature requires a paid plan. Upgrade to continue.")
    return user

def require_plan(min_plan: str):
    def checker(user: AuthUser = Depends(get_current_user_from_request)):
        plan = str(getattr(user, "plan", "free") or "free").lower()
        if PLAN_RANK.get(plan, 0) < PLAN_RANK.get(min_plan.lower(), 0):
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=f"This feature requires {min_plan} or higher. Upgrade to continue.")
        return user
    return checker

def require_admin(user: AuthUser = Depends(get_current_user_from_request)):
    role = getattr(user, "role", None)
    is_admin = role == UserRole.ADMIN or str(role).lower() in ("admin", "userrole.admin")
    if not is_admin:
        raise _forbidden("Admin only.")
    return user

def require_email_verified(user: AuthUser = Depends(get_current_user_from_request)):
    if not getattr(user, "email_verified", False):
        raise _forbidden("Verify your email first. Check your inbox.")
    return user
