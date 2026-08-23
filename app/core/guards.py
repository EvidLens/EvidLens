from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel import Session, select
from app.core.models import Module, UserSubscription, User
from app.core.db import get_session
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"

def get_current_user(request: Request, db: Session = Depends(get_session)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    request.state.user = user
    request.state.db = db
    return user

def require_module(module_number_or_key):
    # Support both int (old) and str key (12 engines new)
    if isinstance(module_number_or_key, str):
        module_key = module_number_or_key
        def decorator_key(func):
            async def wrapper_key(request: Request, *args, **kwargs):
                try:
                    from app.modules.billing.plans import PLAN_MODULES
                except:
                    PLAN_MODULES = {}
                user = getattr(request.state, 'user', None)
                if not user:
                    raise HTTPException(status_code=401, detail="Not authenticated")
                db: Session = getattr(request.state, 'db', None)
                plan = "trial"
                try:
                    if db is not None:
                        sub = db.exec(select(UserSubscription).where(UserSubscription.user_id == user.id)).first()
                        if sub:
                            plan = getattr(sub, 'plan_code', getattr(sub, 'plan', 'trial')).lower().replace('ev-','').replace('ev','')
                            # map ev codes to starter/growth/enterprise
                            code_map = {"free":"trial","starter":"starter","sme":"growth","growth":"growth","pro":"growth","ent":"enterprise","enterprise":"enterprise"}
                            plan = code_map.get(plan, plan)
                            # fallback to PLAN_MODULES keys
                            if plan not in PLAN_MODULES:
                                # try original plan_code ranking fallback
                                rank = {"ev-free":0,"ev-starter":1,"ev-sme":2,"ev-growth":3,"ev-pro":4,"ev-ent":5}
                                # if old plan_code present, convert
                                orig_code = getattr(sub, 'plan_code', '').upper()
                                if orig_code == "EV-FREE": plan = "trial"
                                elif orig_code in ["EV-STARTER"]: plan = "starter"
                                elif orig_code in ["EV-SME","EV-GROWTH","EV-PRO"]: plan = "growth"
                                elif orig_code in ["EV-ENT"]: plan = "enterprise"
                except Exception as e:
                    print(f"plan lookup fail {e}")
                allowed = PLAN_MODULES.get(plan, PLAN_MODULES.get("trial", []))
                if module_key not in allowed:
                    raise HTTPException(status_code=403, detail=f"Module {module_key} not in {plan} plan. Upgrade to access all 12 engines.")
                return await func(request, *args, **kwargs)
            return wrapper_key
        return decorator_key
    else:
        module_number = module_number_or_key
        def decorator(func):
            async def wrapper(request: Request, *args, **kwargs):
                session: Session = request.state.db
                user_id = request.state.user.id
                sub = session.exec(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()
                if not sub:
                    raise HTTPException(status_code=401, detail="No subscription")
                module = session.exec(select(Module).where(Module.module_number == module_number)).first()
                if not module:
                    raise HTTPException(status_code=500, detail=f"Module {module_number} not found in DB")
                rank = {"EV-FREE":0,"EV-STARTER":1,"EV-SME":2,"EV-GROWTH":3,"EV-PRO":4,"EV-ENT":5}
                if rank.get(sub.plan_code,0) < rank.get(module.min_plan,0):
                    raise HTTPException(status_code=403, detail=f"Upgrade to {module.min_plan} to access this module")
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator

def require_module_key(module_key: str):
    # FastAPI Depends version for routers using Depends()
    def _check(request: Request, db: Session = Depends(get_session), user: User = Depends(get_current_user)):
        try:
            from app.modules.billing.plans import PLAN_MODULES
        except:
            PLAN_MODULES = {}
        plan = "trial"
        try:
            sub = db.exec(select(UserSubscription).where(UserSubscription.user_id == user.id)).first()
            if sub:
                raw = getattr(sub, 'plan_code', getattr(sub, 'plan', 'trial'))
                raw = str(raw).lower()
                code_map = {"ev-free":"trial","free":"trial","ev-starter":"starter","starter":"starter","ev-sme":"growth","sme":"growth","ev-growth":"growth","growth":"growth","ev-pro":"growth","pro":"growth","ev-ent":"enterprise","ent":"enterprise","enterprise":"enterprise"}
                plan = code_map.get(raw, raw)
        except:
            pass
        allowed = PLAN_MODULES.get(plan, [])
        if module_key not in allowed:
            raise HTTPException(status_code=403, detail=f"Module {module_key} requires upgrade. Current plan {plan}")
        return user
    return _check

def consume_credits(session: Session, user_id: int, credit_type: str, amount: int):
    sub = session.exec(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()
    if not sub:
        raise HTTPException(status_code=401, detail="No subscription")
    credits = getattr(sub, credit_type, None)
    if credits is None:
        raise HTTPException(status_code=500, detail=f"Credit type {credit_type} not found")
    if credits < amount:
        raise HTTPException(status_code=402, detail="Not enough credits. Please buy more.")
    setattr(sub, credit_type, credits - amount)
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub
