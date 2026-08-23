from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

PUBLIC_PATHS = ["/auth/login","/auth/register","/auth/signup","/auth/verify","/auth/forgot","/auth/reset","/pricing","/health","/docs","/redoc","/openapi.json","/static","/login","/register"]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATHS) or path == "/":
            return await call_next(request)
        user_id = request.cookies.get("user_id") or request.cookies.get("access_token")
        auth = request.headers.get("Authorization")
        if not user_id and not auth:
            if path.startswith("/api/") or path.startswith("/reports/generate"):
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
            # accept header check
            if "text/html" in request.headers.get("accept",""):
                return RedirectResponse(url="/auth/login?next="+path, status_code=302)
        return await call_next(request)
