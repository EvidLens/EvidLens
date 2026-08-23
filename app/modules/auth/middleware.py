from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

PUBLIC_PATHS = [
    "/auth/login",
    "/auth/register",
    "/auth/signup",
    "/auth/verify",
    "/auth/forgot",
    "/auth/reset",
    "/auth/logout",
    "/pricing",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
    "/login",
    "/register"
    # DO NOT PUT "/" HERE
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        
        # Public check - exact or startswith + slash
        is_public = any(
            path == p or path.startswith(p + "/") 
            for p in PUBLIC_PATHS
        )
        if is_public:
            return await call_next(request)
        
        user_id = request.cookies.get("user_id") or request.cookies.get("access_token")
        auth = request.headers.get("Authorization")
        
        if not user_id and not auth:
            if path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
            # For ALL pages including "/" and /location, /market etc -> login
            return RedirectResponse(url=f"/auth/login?next={path}", status_code=302)
        
        return await call_next(request)
