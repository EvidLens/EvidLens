from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

PUBLIC_PATHS = [
    "/auth",              # /auth/login, /auth/signup, /auth/verify, /auth/forgot-password, /auth/reset-password, /auth/admin/fix-login
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
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # allow all public paths
        if any(path == p or path.startswith(p + "/") or path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # root "/" requires login
        if path == "/":
            user_id = request.cookies.get("user_id") or request.cookies.get("access_token")
            auth = request.headers.get("Authorization")
            if not user_id and not auth:
                return RedirectResponse(url="/auth/login", status_code=302)
            return await call_next(request)

        # check auth
        user_id = request.cookies.get("user_id") or request.cookies.get("access_token")
        auth = request.headers.get("Authorization")

        if not user_id and not auth:
            if path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
            return RedirectResponse(url=f"/auth/login?next={path}", status_code=302)

        return await call_next(request)
