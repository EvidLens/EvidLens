from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, text
from pydantic import BaseModel, EmailStr
from.service import *
from.models import AuthUser
from.dependencies import get_current_user, require_active_subscription, require_admin
from app.core.db import get_session as get_db
import secrets
import os
import resend
import uuid
from datetime import datetime
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")

# --- EMAIL CONFIG ---
RESEND_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@evidlens.co.ke")
FROM_NAME = os.getenv("FROM_NAME", "EvidLens")
APP_URL = os.getenv("APP_URL", "https://app.evidlens.co.ke")

if RESEND_KEY:
    resend.api_key = RESEND_KEY

# --- GOOGLE OAUTH CONFIG ---
config = Config('.env')
oauth = OAuth(config)
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def send_verification_email(to: str, name: str, token: str):
    if not RESEND_KEY:
        print(f"[EMAIL SKIP] No RESEND_API_KEY - verify token: {token}")
        return
    verify_url = f"{APP_URL}/auth/verify?token={token}"
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden">
      <div style="background:#0B1220;padding:24px;text-align:center">
        <img src="{APP_URL}/static/logo.png" alt="EvidLens" style="height:40px;background:white;border-radius:8px;padding:6px">
        <h1 style="color:white;margin:12px 0 0;font-size:20px">EvidLens</h1>
      </div>
      <div style="padding:32px">
        <h2 style="color:#0f172a;margin:0 0 12px">Welcome, {name}!</h2>
        <p style="color:#475569;font-size:14px;line-height:1.6">Thanks for requesting access to EvidLens Decision Intelligence OS. Please verify your email to activate your account.</p>
        <div style="text-align:center;margin:28px 0">
          <a href="{verify_url}" style="display:inline-block;background:#14B8A6;color:white;padding:14px 28px;border-radius:12px;text-decoration:none;font-weight:700;font-size:14px">Verify Email Address</a>
        </div>
        <p style="color:#64748b;font-size:13px">Or copy this link: <br><a href="{verify_url}" style="color:#0d9488;word-break:break-all">{verify_url}</a></p>
        <p style="color:#94a3b8;font-size:12px;margin-top:24px">Link expires in 24 hours. If you didn't request this, ignore this email.<br><br>Support: support@evidlens.co.ke<br>© 2026 EvidLens Ltd • KDPA Compliant • ODPC Registered</p>
      </div>
    </div>
    """
    try:
        resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to],
            "subject": "Verify your EvidLens account",
            "html": html
        })
        print(f"[EMAIL SENT] Verification to {to} via {FROM_EMAIL}")
    except Exception as e:
        print(f"[EMAIL FAILED] {to}: {e}")

def send_reset_email(to: str, token: str):
    if not RESEND_KEY:
        print(f"[EMAIL SKIP] Reset token: {token}")
        return
    reset_url = f"{APP_URL}/reset-password?token={token}"
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto">
      <h2>Reset your EvidLens password</h2>
      <p>Click below to reset. Link expires in 30 minutes.</p>
      <a href="{reset_url}" style="display:inline-block;background:#14B8A6;color:white;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:600">Reset Password</a>
      <p style="font-size:12px;color:#64748b;margin-top:20px">{reset_url}</p>
    </div>
    """
    try:
        resend.Emails.send({"from": f"{FROM_NAME} <{FROM_EMAIL}>","to": [to],"subject": "Reset your EvidLens password","html": html})
        print(f"[EMAIL SENT] Reset to {to}")
    except Exception as e:
        print(f"Reset email failed: {e}")

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    sector: str
    county: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotRequest(BaseModel):
    email: EmailStr

class ResetRequest(BaseModel):
    token: str
    new_password: str

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class ProfileUpdateRequest(BaseModel):
    full_name: str
    phone: str
    theme: str
    language: str

@router.post("/signup")
def signup(req: SignupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    token = secrets.token_urlsafe(32)
    user = create_user(db, req, token)
    background_tasks.add_task(send_verification_email, user.email, user.full_name or "there", token)
    return {"message": f"Verification email sent from {FROM_EMAIL}. Check inbox.", "email": user.email}

@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = verify_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    return RedirectResponse(url="/auth/login?verified=1", status_code=302)

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(db, req.email, req.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    response = JSONResponse(content=result)
    response.set_cookie(
        key="user_id",
        value=str(result["user_id"]),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400*7,
        path="/"
    )
    return response

@router.post("/forgot-password")
def forgot(req: ForgotRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    result = request_password_reset(db, req.email)
    if "reset_token" in result:
        background_tasks.add_task(send_reset_email, req.email, result["reset_token"])
    return {"message": f"If email exists, reset link sent from {FROM_EMAIL}"}

@router.post("/reset-password")
def reset(req: ResetRequest, db: Session = Depends(get_db)):
    result = reset_password(db, req.token, req.new_password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/change-password")
def change_password(req: PasswordChangeRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    result = update_password(db, user, req.old_password, req.new_password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/update-profile")
def update_profile_route(req: ProfileUpdateRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_profile(db, user, req.full_name, req.phone, req.theme, req.language)

@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    return user

@router.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("user_id", path="/")
    return response

@router.get("/logout")
def logout_get():
    response = RedirectResponse(url="/auth/login")
    response.delete_cookie("user_id", path="/")
    return response

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# --- GOOGLE OAUTH ROUTES ---
@router.get("/oauth/google")
async def oauth_google(request: Request):
    redirect_uri = f"{APP_URL}/auth/oauth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/oauth/google/callback")
async def oauth_google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            user_info = await oauth.google.parse_id_token(request, token)

        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])

        user = get_user_by_email(db, email)
        if not user:
            user_id = str(uuid.uuid4())
            db.exec(text(f"INSERT INTO auth_user (id, email, full_name, hashed_password, email_verified, is_active, sector, county, theme, language) VALUES (:id, :email, :name, '', true, true, 'general', 'Nairobi', 'light', 'en')"), {"id": user_id, "email": email, "name": name})
            db.commit()
            user = get_user_by_email(db, email)
            if not user:
                # fallback fetch
                res = db.exec(text("SELECT * FROM auth_user WHERE email = :email"), {"email": email}).first()
                user = res

        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="user_id",
            value=str(user.id if hasattr(user, 'id') else user[0]),
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400*7,
            path="/"
        )
        return response
    except Exception as e:
        print(f"[OAUTH ERROR] {e}")
        return RedirectResponse(url=f"/auth/login?error=oauth_failed&detail={str(e)[:100]}", status_code=302)

# ADMIN FIX
@router.get("/admin/fix-login")
def fix_login(db: Session = Depends(get_db), admin: AuthUser = Depends(require_admin)):
    db.exec(text("UPDATE auth_user SET email_verified = true, is_active = true WHERE email_verified = false"))
    db.exec(text(f"DELETE FROM auth_user WHERE email = :email"), {"email": FROM_EMAIL})
    db.commit()
    users = db.exec(text("SELECT id, email, email_verified, is_active FROM auth_user")).all()
    return {"fixed": True, "message": "Verified existing users - passwords preserved", "users": [{"id": u[0], "email": u[1], "verified": u[2], "active": u[3]} for u in users]}

@router.get("/admin/clear-cache")
def clear_cache(db: Session = Depends(get_db), admin: AuthUser = Depends(require_admin)):
    db.exec(text("TRUNCATE TABLE auth_user RESTART IDENTITY CASCADE"))
    db.commit()
    response = JSONResponse(content={"cleared": True, "message": "All users cleared - fresh signup required"})
    response.delete_cookie("user_id", path="/")
    return response
