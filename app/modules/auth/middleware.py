from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

PUBLIC_PATHS = [
    "/auth",
    "/login",
    "/register",
    "/signup",
    "/signin",
    "/do-login",
    "/do-signup",
    "/forgot-password",
    "/forgot",
    "/reset-password",
    "/privacy",
    "/terms",
    "/dpa",
    "/pricing",
    "/welcome",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
    "/favicon.ico",
    "/robots.txt",
    "/api/auth",
    "/api/public",
]

PROTECTED_PAGE_PREFIXES = [
    "/dashboard",
    "/competitive",
    "/market",
    "/location",
    "/voice",
    "/kb",
    "/policy",
    "/reports",
    "/funding",
    "/history",
    "/stats",
    "/settings",
    "/wallet",
    "/workspaces",
    "/ai",
    "/billing",
    "/about",
    "/contact",
    "/help",
    "/changelog",
    "/security",
    "/risk",
]

PUBLIC_READ_API_PREFIXES = [
    "/api/data/",
    "/api/meta/",
    "/analysis/",
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        for p in PUBLIC_PATHS:
            if path == p or path.startswith(p + "/"):
                return await call_next(request)
        has_auth = False
        # 1. Session
        try:
            if request.session.get("user_id"):
                has_auth = True
        except Exception:
            pass
        # 2. COOKIES - THIS WAS MISSING. This is what survives restarts.
        if not has_auth:
            for key in ("user_id", "session", "auth_user_id"):
                v = request.cookies.get(key)
                if v and str(v).isdigit():
                    has_auth = True
                    break
        # 3. Bearer
        if not has_auth:
            auth = request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                token = auth.replace("Bearer ", "").strip()
                if token.isdigit():
                    has_auth = True
        if path == "/":
            return await call_next(request)
        is_protected_page = False
        for prefix in PROTECTED_PAGE_PREFIXES:
            if path == prefix or path.startswith(prefix + "/"):
                is_protected_page = True
                break
        if is_protected_page:
            if not has_auth:
                accept = request.headers.get("accept", "")
                if "text/html" in accept or "text/" in accept or accept == "" or "*/*" in accept:
                    return RedirectResponse(url="/login", status_code=302)
                return JSONResponse(status_code=401, content={"detail": "Not authenticated - please login"})
            return await call_next(request)
        if path.startswith("/api/"):
            if not has_auth:
                for pub in PUBLIC_READ_API_PREFIXES:
                    if path.startswith(pub):
                        return await call_next(request)
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        return await call_next(request)
