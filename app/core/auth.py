from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(request: Request):
    user_id = getattr(request.state, "user", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
