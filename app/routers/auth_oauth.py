from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
MS_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
BASE_URL = os.getenv("BASE_URL", "https://app.evidlens.co.ke").rstrip("/")

@router.get("/auth/oauth/google")
async def oauth_google():
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse("/auth/login?error=sso_not_configured")
    redirect_uri = f"{BASE_URL}/auth/callback/google"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code&scope=openid email profile"
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
        f"&response_type=code&scope=openid email profile"
        f"&response_mode=query"
    )
    return RedirectResponse(url)

@router.get("/auth/callback/{provider}")
async def oauth_callback(provider: str, code: str = None, request: Request = None):
    # TODO: exchange code for user info and create session
    # For now just redirect to login with success to stop 404
    if not code:
        return RedirectResponse("/auth/login?error=oauth_failed")
    return RedirectResponse("/?oauth=success")
