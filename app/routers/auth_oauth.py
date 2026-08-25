from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import os
import requests
from sqlmodel import Session, select
from app.core.db import get_session as get_db
from app.modules.auth.models import AuthUser, UserRole
from datetime import datetime

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
MS_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MS_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "https://app.evidlens.co.ke").rstrip("/")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@evidlens.co.ke")

def get_or_create_oauth_user(db: Session, email: str, full_name: str, provider: str):
    email = email.lower().strip()
    user = db.exec(select(AuthUser).where(AuthUser.email == email)).first()
    admin_emails = [e.strip().lower() for e in ADMIN_EMAIL.split(",") if e.strip()]
    is_admin = email in admin_emails or email == FROM_EMAIL.lower()

    if not user:
        # Create new oauth user with random password placeholder
        user = AuthUser(
            email=email,
            full_name=full_name,
            phone="",
            sector="",
            county="",
            hashed_password="oauth_no_password",
            verification_token=None,
            role=UserRole.ADMIN if is_admin else UserRole.USER,
            is_active=True,
            email_verified=True,
            credits=999999 if is_admin else 5,
            plan="enterprise" if is_admin else "free"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OAUTH CREATED] {email} via {provider} as {user.role}")
    else:
        # Ensure existing user is verified and active
        if not user.email_verified or not user.is_active:
            user.email_verified = True
            user.is_active = True
            db.add(user)
            db.commit()
            db.refresh(user)
    return user

@router.get("/auth/oauth/google")
async def oauth_google():
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse("/auth/login?error=sso_not_configured")
    redirect_uri = f"{BASE_URL}/auth/callback/google"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code&scope=openid%20email%20profile"
        f"&access_type=offline&prompt=select_account"
    )
    return RedirectResponse(url)

@router.get("/auth/oauth/microsoft")
async def oauth_microsoft():
    if not MS_CLIENT_ID:
        return RedirectResponse("/auth/login?error=sso_not_configured")
    redirect_uri = f"{BASE_URL}/auth/callback/microsoft"
    url = (
        f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        f"?client_id={MS_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code&scope=openid%20email%20profile%20User.Read"
        f"&response_mode=query"
    )
    return RedirectResponse(url)

@router.get("/auth/callback/google")
async def oauth_callback_google(code: str = None, request: Request = None, db: Session = Depends(get_db)):
    if not code:
        return RedirectResponse("/auth/login?error=oauth_failed")
    
    redirect_uri = f"{BASE_URL}/auth/callback/google"
    
    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    try:
        r = requests.post(token_url, data=data, timeout=10)
        tokens = r.json()
        access_token = tokens.get("access_token")
        if not access_token:
            print(f"[GOOGLE OAUTH ERROR] {tokens}")
            return RedirectResponse("/auth/login?error=oauth_token_failed")
        
        # Get user info
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        ).json()
        
        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("given_name") or email
        
        if not email:
            return RedirectResponse("/auth/login?error=oauth_no_email")
        
        user = get_or_create_oauth_user(db, email, name, "google")
        
        # Create login response with cookie
        response = RedirectResponse(url="/?oauth=success", status_code=302)
        response.set_cookie(
            key="user_id",
            value=str(user.id),
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400*7,
            path="/"
        )
        return response
        
    except Exception as e:
        print(f"[GOOGLE CALLBACK ERROR] {e}")
        return RedirectResponse("/auth/login?error=oauth_exception")

@router.get("/auth/callback/microsoft")
async def oauth_callback_microsoft(code: str = None, request: Request = None, db: Session = Depends(get_db)):
    if not code:
        return RedirectResponse("/auth/login?error=oauth_failed")
    
    redirect_uri = f"{BASE_URL}/auth/callback/microsoft"
    
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        "code": code,
        "client_id": MS_CLIENT_ID,
        "client_secret": MS_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "scope": "openid email profile User.Read"
    }
    try:
        r = requests.post(token_url, data=data, timeout=10)
        tokens = r.json()
        access_token = tokens.get("access_token")
        if not access_token:
            print(f"[MS OAUTH ERROR] {tokens}")
            return RedirectResponse("/auth/login?error=oauth_token_failed")
        
        # Get user info from Microsoft Graph
        user_info = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        ).json()
        
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        name = user_info.get("displayName") or email
        
        if not email:
            return RedirectResponse("/auth/login?error=oauth_no_email")
        
        user = get_or_create_oauth_user(db, email, name, "microsoft")
        
        response = RedirectResponse(url="/?oauth=success", status_code=302)
        response.set_cookie(
            key="user_id",
            value=str(user.id),
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400*7,
            path="/"
        )
        return response
        
    except Exception as e:
        print(f"[MS CALLBACK ERROR] {e}")
        return RedirectResponse("/auth/login?error=oauth_exception")

@router.get("/auth/callback/{provider}")
async def oauth_callback_generic(provider: str, code: str = None):
    if not code:
        return RedirectResponse("/auth/login?error=oauth_failed")
    return RedirectResponse("/?oauth=success")
