from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def require_active_subscription(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials
