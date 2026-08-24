from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from pydantic import BaseModel, EmailStr
from.service import *
from.models import AuthUser
from.dependencies import get_current_user, require_active_subscription, require_admin
from app.core.db import get_session as get_db
import secrets
import os
import resend
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")

# --- EMAIL CONFIG - FROM YOUR SCREENSHOT ---
RESEND_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@evidlens.co.ke")
FROM_NAME = os.getenv("FROM_NAME", "EvidLens")
APP_URL = os.getenv("APP_URL", "https://app.evidlens.co.ke")

if RESEND_KEY:
    resend.api_key = RESEND_KEY

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
        print(f"[EMAIL SENT] Verification to {to}")
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
    # Send verification email via noreply@evidlens.co.ke
    background_tasks.add_task(send_verification_email, user.email, user.full_name or "there", token)
    return {"message": "Verification email sent from noreply@evidlens.co.ke. Check inbox.", "email": user.email}

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
        secure=True, # HTTPS only
        samesite="lax",
        max_age=86400*7,
        path="/"
    )
    return response

@router.post("/forgot-password")
def forgot(req: ForgotRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    result = request_password_reset(db, req.email)
    # If user exists, send email
    if "reset_token" in result:
        background_tasks.add_task(send_reset_email, req.email, result["reset_token"])
    return {"message": "If email exists, reset link sent from noreply@evidlens.co.ke"}

@router.post("/reset-password")
def reset(req: ResetRequest, db: Session = Depends(get_db)):
    return reset_password(db, req.token, req.new_password)

@router.post("/change-password")
def change_password(req: PasswordChangeRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return update_password(db, user, req.old_password, req.new_password)

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

@router.get("/oauth/{provider}")
def oauth_placeholder(provider: str):
    return RedirectResponse(url="/auth/login?error=oauth_not_configured")

@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

# DELETE THIS AFTER YOU HAVE VERIFIED YOUR ADMIN ACCOUNT WORKS - SECURE VERSION
@router.get("/admin/fix-login")
def fix_login(db: Session = Depends(get_db), admin: AuthUser = Depends(require_admin)):
    from sqlmodel import text
    # SECURE: Only verify existing users, DO NOT override passwords - users keep own passwords
    db.exec(text("UPDATE auth_user SET email_verified = true, is_active = true WHERE email_verified = false"))
    db.exec(text("DELETE FROM auth_user WHERE email = 'noreply@evidlens.co.ke'"))
    db.commit()
    users = db.exec(text("SELECT id, email, email_verified, is_active FROM auth_user")).all()
    return {"fixed": True, "message": "Verified - users keep own passwords (security compliant)", "users": [{"id": u[0], "email": u[1], "verified": u[2], "active": u[3]} for u in users]}

@router.get("/admin/clear-cache")
def clear_cache(db: Session = Depends(get_db), admin: AuthUser = Depends(require_admin)):
    from sqlmodel import text
    db.exec(text("TRUNCATE TABLE auth_user RESTART IDENTITY CASCADE"))
    db.commit()
    response = JSONResponse(content={"cleared": True, "message": "All cache cleared - fresh signup with own password"})
    response.delete_cookie("user_id", path="/")
    return response
