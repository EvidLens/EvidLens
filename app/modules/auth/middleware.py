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
    "/reset-password",
    "/privacy",
    "/terms",
    "/dpa",
    "/pricing",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
    # --- KEEP ALL 6 - ADDED SO THEY NEVER BOUNCE TO LOGIN ---
    "/market/demand",      # Demand Radar - KEEP
    "/voice",              # Consumer Pulse - KEEP
    "/kb",                 # Knowledge Base - KEEP + /kb/policy
    "/policy",             # Policy Watch - KEEP
    "/reports",            # Report Builder - KEEP
    "/reports/funding",    # Funding Radar - KEEP
    "/funding",            # Funding Radar alias - KEEP
    # --- Other dashboard pages - also keep open ---
    "/",
    "/competitive",
    "/market/prices",
    "/market/export",
    "/market/risk",
    "/risk",
    "/location/counties",
    "/history",
    "/stats",
    "/about",
    "/contact",
    "/help",
    "/billing",
    "/changelog",
    "/security",
    "/settings",
    "/wallet",
    "/workspaces",
    "/ai",
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # allow all public / dashboard pages - NEVER bounce these
        for p in PUBLIC_PATHS:
            if path == p or path.startswith(p + "/") or path == p + "/":
                return await call_next(request)

        # only protect real API + Business OS actions
        # page views are public, generating/downloading still checks login inside the router
        if path.startswith("/api/"):
            user_id = request.cookies.get("user_id") or request.cookies.get("access_token")
            auth = request.headers.get("Authorization")
            if not user_id and not auth:
                # allow public read APIs so dashboard counts load
                if path.startswith("/api/data/") or path.startswith("/api/meta/") or path.startswith("/analysis/"):
                    return await call_next(request)
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        return await call_next(request)
