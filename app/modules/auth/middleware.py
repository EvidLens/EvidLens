from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

PUBLIC_PATHS = [
    "/auth",          # allows /auth/login, /auth/register, /auth/verify, /auth/logout, /do-login
    "/login",
    "/register", 
    "/signup",        # your signup page
    "/signin",
    "/do-login",      # your login POST
    "/do-signup",
    "/pricing",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        
        is_public = any(path == p or path.startswith(p + "/") or path.startswith(p) for p in PUBLIC_PATHS)
        # simpler: check startswith
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)
        
        if path == "/":
            is_public = False
        
        user_id = request.cookies.get("user_id") or request.cookies.get("access_token")
        auth = request.headers.get("Authorization")
        
        if not user_id and not auth:
            if path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
            return RedirectResponse(url=f"/auth/login?next={path}", status_code=302)
        
        return await call_next(request)
