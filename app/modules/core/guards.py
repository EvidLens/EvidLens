from fastapi import Request, HTTPException
from sqlmodel import Session, select
from app.modules.core.models import Module, UserSubscription

def require_module(module_number: int):
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            session: Session = request.state.db
            user_id = request.state.user.id
            sub = session.exec(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()
            if not sub: raise HTTPException(status_code=401, detail="No subscription")
            module = session.exec(select(Module).where(Module.module_number == module_number)).first()
            rank = {"EV-FREE":0,"EV-STARTER":1,"EV-SME":2,"EV-GROWTH":3,"EV-PRO":4,"EV-ENT":5}
            if rank.get(sub.plan_code,0) < rank.get(module.min_plan,0):
                raise HTTPException(status_code=403, detail=f"Upgrade to {module.min_plan} to access this module")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def consume_credits(session: Session, user_id: int, credit_type: str, amount: int):
    sub = session.exec(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()
    credits = getattr(sub, credit_type)
    if credits < amount: 
        raise HTTPException(status_code=402, detail="Not enough credits. Please buy more.")
    setattr(sub, credit_type, credits - amount)
    session.add(sub)
    session.commit()
