from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
import os
import secrets
import requests
from sqlmodel import Session, select
from app.core.db import get_session as get_db
from app.modules.auth.models import AuthUser, UserRole
from urllib.parse import urlencode

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
MS_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "https://app.evidlens.co.ke").rstrip("/")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
COOKIE_SECURE = BASE_URL.startswith("https://")

def _admin_emails():
    return [e.strip().lower() for e in ADMIN_EMAIL.split(",") if e.strip()]

def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/"

def _set_state_cookie(response: RedirectResponse, provider: str, next_url: str) -> str:
    state = secrets.token_urlsafe(32)
    response.set_cookie(key=f"oauth_state_{provider}", value=state, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=600, path="/")
    response.set_cookie(key="oauth_next", value=_safe_next(next_url), httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=600, path="/")
    return state

def _check_state(request: Request, provider: str, state: str | None) -> bool:
    expected = request.cookies.get(f"oauth_state_{provider}")
    return bool(state and expected and secrets.compare_digest(state, expected))

def _clear_state_cookies(response: RedirectResponse, provider: str):
    response.delete_cookie(key=f"oauth_state_{provider}", path="/")
    response.delete_cookie(key="oauth_next", path="/")
    return response

def _login_response(user: AuthUser, next_url: str, provider: str) -> RedirectResponse:
    response = RedirectResponse(url=f"{_safe_next(next_url)}?oauth=success", status_code=302)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=86400 * 7, path="/")
    return _clear_state_cookies(response, provider)

def get_or_create_oauth_user(db: Session, email: str, full_name: str, provider: str):
    email = email.lower().strip()
    user = db.exec(select(AuthUser).where(AuthUser.email == email)).first()
    is_admin = email in _admin_emails()
    if not user:
        user = AuthUser(
            email=email,
            full_name=full_name[:100] if full_name else email,
            phone="",
            sector="",
            county="",
            hashed_password="oauth_no_password",
            verification_token=None,
            role=UserRole.ADMIN if is_admin else UserRole.USER,
            is_active=True,
            email_verified=True,
            credits=5,
            plan="free"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OAUTH CREATED] {email} via {provider} as {user.role}")
    else:
        changed = False
        if not user.email_verified:
            user.email_verified = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if is_admin and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            changed = True
        if changed:
            db.add(user)
            db.commit()
            db.refresh(user)
    return user

@router.get("/auth/oauth/google")
async def oauth_google(request: Request, next: str | None = None):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse("/login?error=sso_not_configured")
    redirect_uri = f"{BASE_URL}/auth/callback/google"
    response = RedirectResponse(url="https://accounts.google.com/o/oauth2/v2/auth", status_code=302)
    state = _set_state_cookie(response, "google", next or "/")
    params = {"client_id": GOOGLE_CLIENT_ID, "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile", "access_type": "offline", "prompt": "select_account", "state": state}
    response.headers["Location"] = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return response

@router.get("/auth/oauth/microsoft")
async def oauth_microsoft(request: Request, next: str | None = None):
    if not MS_CLIENT_ID or not MS_CLIENT_SECRET:
        return RedirectResponse("/login?error=sso_not_configured")
    redirect_uri = f"{BASE_URL}/auth/callback/microsoft"
    response = RedirectResponse(url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize", status_code=302)
    state = _set_state_cookie(response, "microsoft", next or "/")
    params = {"client_id": MS_CLIENT_ID, "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile User.Read", "response_mode": "query", "state": state}
    response.headers["Location"] = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"
    return response

@router.get("/auth/callback/google")
async def oauth_callback_google(request: Request, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error:
        return RedirectResponse(f"/login?error=oauth_{error}")
    if not code or not _check_state(request, "google", state):
        return RedirectResponse("/login?error=oauth_state_mismatch")
    redirect_uri = f"{BASE_URL}/auth/callback/google"
    data = {"code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uri": redirect_uri, "grant_type": "authorization_code"}
    try:
        r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=10)
        tokens = r.json() if r.content else {}
        if r.status_code != 200:
            print(f"[GOOGLE OAUTH ERROR] {tokens}")
            return RedirectResponse("/login?error=oauth_token_failed")
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token")
        if not access_token and not id_token:
            return RedirectResponse("/login?error=oauth_token_failed")
        email = None
        name = None
        if id_token:
            try:
                verify = requests.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}, timeout=10)
                info = verify.json() if verify.content else {}
                if verify.status_code == 200 and info.get("aud") == GOOGLE_CLIENT_ID and info.get("email_verified") == "true":
                    email = info.get("email")
                    name = info.get("name")
            except Exception:
                email = None
        if not email and access_token:
            user_info = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
            info = user_info.json() if user_info.content else {}
            if user_info.status_code == 200 and info.get("verified_email"):
                email = info.get("email")
                name = info.get("name") or info.get("given_name")
        if not email:
            return RedirectResponse("/login?error=oauth_no_email")
        user = get_or_create_oauth_user(db, email, name or email, "google")
        next_url = request.cookies.get("oauth_next") or "/"
        return _login_response(user, next_url, "google")
    except Exception as e:
        print(f"[GOOGLE CALLBACK ERROR] {e}")
        return RedirectResponse("/login?error=oauth_exception")

@router.get("/auth/callback/microsoft")
async def oauth_callback_microsoft(request: Request, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error:
        return RedirectResponse(f"/login?error=oauth_{error}")
    if not code or not _check_state(request, "microsoft", state):
        return RedirectResponse("/login?error=oauth_state_mismatch")
    redirect_uri = f"{BASE_URL}/auth/callback/microsoft"
    data = {"code": code, "client_id": MS_CLIENT_ID, "client_secret": MS_CLIENT_SECRET, "redirect_uri": redirect_uri, "grant_type": "authorization_code", "scope": "openid email profile User.Read"}
    try:
        r = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data=data, timeout=10)
        tokens = r.json() if r.content else {}
        if r.status_code != 200:
            print(f"[MS OAUTH ERROR] {tokens}")
            return RedirectResponse("/login?error=oauth_token_failed")
        access_token = tokens.get("access_token")
        if not access_token:
            return RedirectResponse("/login?error=oauth_token_failed")
        user_info = requests.get("https://graph.microsoft.com/v1.0/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        info = user_info.json() if user_info.content else {}
        if user_info.status_code != 200:
            return RedirectResponse("/login?error=oauth_token_failed")
        email = info.get("mail") or info.get("userPrincipalName")
        name = info.get("displayName") or email
        if not email or "@" not in email:
            return RedirectResponse("/login?error=oauth_no_email")
        user = get_or_create_oauth_user(db, email, name, "microsoft")
        next_url = request.cookies.get("oauth_next") or "/"
        return _login_response(user, next_url, "microsoft")
    except Exception as e:
        print(f"[MS CALLBACK ERROR] {e}")
        return RedirectResponse("/login?error=oauth_exception")
