from sqlmodel import Session, select
import bcrypt
from.models import AuthUser, UserRole
import requests, os
from datetime import datetime, timedelta

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@evidlens.co.ke")
FROM_NAME = os.getenv("FROM_NAME", "EvidLens")
APP_URL = os.getenv("APP_URL", "https://app.evidlens.co.ke")

def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY:
        print(f"[EMAIL MOCK] to {to} subject {subject}")
        return
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [to], "subject": subject, "html": html},
            timeout=10
        )
        print(f"[EMAIL] {to} -> {resp.status_code}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

def hash_password(password: str):
    pw = password.encode('utf-8')[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
    except:
        return False

def get_user_by_email(db: Session, email: str):
    return db.exec(select(AuthUser).where(AuthUser.email == email.lower().strip())).first()

def create_user(db: Session, req, token: str):
    hashed_pw = hash_password(req.password)
    db_user = AuthUser(
        email=req.email.lower().strip(),
        phone=req.phone,
        hashed_password=hashed_pw,
        full_name=req.full_name,
        sector=req.sector,
        county=req.county,
        verification_token=token,
        role=UserRole.USER,
        is_active=True,
        email_verified=False,
        credits=5,
        plan="free"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    verify_link = f"{APP_URL}/auth/verify?token={token}"
    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden">
      <div style="background:#0B1220;padding:24px;text-align:center">
        <img src="{APP_URL}/static/logo.png" style="height:40px;background:white;border-radius:8px;padding:6px" alt="EvidLens">
      </div>
      <div style="padding:32px">
        <h2>Welcome, {req.full_name}!</h2>
        <p>Verify your email to activate your EvidLens Decision Intelligence workspace.</p>
        <p style="text-align:center;margin:24px 0"><a href="{verify_link}" style="background:#14B8A6;color:white;padding:14px 28px;border-radius:12px;text-decoration:none;font-weight:700">Verify Email</a></p>
        <p style="font-size:12px;color:#64748b">Link expires in 24h: {verify_link}<br>Support: support@evidlens.co.ke • KDPA Compliant</p>
      </div>
    </div>
    """
    send_email(req.email, "Verify your EvidLens Account", html)
    return db_user

def verify_user(db: Session, token: str):
    user = db.exec(select(AuthUser).where(AuthUser.verification_token == token)).first()
    if not user:
        return None
    user.email_verified = True
    user.verification_token = None
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return {"error": "Invalid credentials"}
    if not user.email_verified:
        return {"error": "Email not verified - check inbox for noreply@evidlens.co.ke"}
    if not user.is_active:
        return {"error": "Account disabled"}
    if not verify_password(password, user.hashed_password):
        return {"error": "Invalid credentials"}
    return {"message": "Login successful", "user_id": user.id, "role": user.role, "email": user.email}

def request_password_reset(db: Session, email: str):
    user = get_user_by_email(db, email)
    if not user:
        return {"message": "If email exists, reset link sent"}
    token = os.urandom(32).hex()
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.add(user)
    db.commit()
    reset_link = f"{APP_URL}/reset-password?token={token}"
    html = f"<div style='font-family:Inter'><h2>Reset Password</h2><p>Click to reset (30 min):</p><p><a href='{reset_link}' style='background:#14B8A6;color:white;padding:12px 24px;border-radius:10px;text-decoration:none'>Reset Password</a></p><p style='font-size:12px;color:#64748b'>{reset_link}</p></div>"
    send_email(email, "Reset your EvidLens Password", html)
    return {"message": "Reset email sent", "reset_token": token}

def reset_password(db: Session, token: str, new_password: str):
    user = db.exec(select(AuthUser).where(AuthUser.reset_token == token, AuthUser.reset_token_expires > datetime.utcnow())).first()
    if not user:
        return {"error": "Invalid or expired token"}
    user.hashed_password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.add(user)
    db.commit()
    return {"message": "Password reset successfully"}

def update_password(db: Session, user: AuthUser, old_password: str, new_password: str):
    if not verify_password(old_password, user.hashed_password):
        return {"error": "Old password incorrect"}
    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.commit()
    return {"message": "Password updated"}

def update_profile(db: Session, user: AuthUser, full_name: str, phone: str, theme: str, language: str):
    user.full_name = full_name
    user.phone = phone
    user.theme = theme
    user.language = language
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Profile updated", "user": user}
