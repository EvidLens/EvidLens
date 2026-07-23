from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from.models import AuthUser, UserRole
from app.modules.database import get_session as get_db
import requests, os
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@evidlens.co.ke")
FROM_NAME = os.getenv("FROM_NAME", "EvidLens")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY: return
    requests.post("https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [to], "subject": subject, "html": html}
    )

def hash_password(password: str):
    if len(password.encode('utf-8')) > 72: password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    if len(plain_password.encode('utf-8')) > 72: plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_email(db: Session, email: str): return db.query(AuthUser).filter(AuthUser.email == email).first()

def create_user(db: Session, req, token: str):
    hashed_pw = hash_password(req.password)
    db_user = AuthUser(email=req.email, phone=req.phone, hashed_password=hashed_pw, full_name=req.full_name, sector=req.sector, county=req.county, verification_token=token, role=UserRole.USER, is_active=True)
    db.add(db_user); db.commit(); db.refresh(db_user)
    verify_link = f"{APP_URL}/auth/verify?token={token}"
    send_email(req.email, "Verify your EvidLens Account", f"<h2>Welcome to EvidLens</h2><p>Click to verify: <a href='{verify_link}'>Verify Email</a></p>")
    return db_user

def verify_user(db: Session, token: str):
    user = db.query(AuthUser).filter(AuthUser.verification_token == token).first()
    if not user: return None
    user.email_verified = True; user.verification_token = None; db.commit(); return user

def login_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user: return {"error": "Invalid credentials"}
    if not user.email_verified: return {"error": "Email not verified"}
    if not verify_password(password, user.hashed_password): return {"error": "Invalid credentials"}
    return {"message": "Login successful", "user_id": user.id, "role": user.role}

def request_password_reset(db: Session, email: str):
    user = get_user_by_email(db, email)
    if not user: return {"message": "If email exists, reset link sent"}
    token = os.urandom(32).hex()
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    reset_link = f"{APP_URL}/reset-password?token={token}"
    send_email(email, "Reset your EvidLens Password", f"<h2>Password Reset</h2><p>Click to reset: <a href='{reset_link}'>Reset Password</a></p><p>Link expires in 1 hour</p>")
    return {"message": "Reset email sent"}

def reset_password(db: Session, token: str, new_password: str):
    user = db.query(AuthUser).filter(AuthUser.reset_token == token, AuthUser.reset_token_expires > datetime.utcnow()).first()
    if not user: return {"error": "Invalid or expired token"}
    user.hashed_password = hash_password(new_password)
    user.reset_token = None; user.reset_token_expires = None; db.commit()
    return {"message": "Password reset successfully"}

def update_password(db: Session, user: AuthUser, old_password: str, new_password: str):
    if not verify_password(old_password, user.hashed_password): return {"error": "Old password incorrect"}
    user.hashed_password = hash_password(new_password); db.commit(); return {"message": "Password updated"}

def update_profile(db: Session, user: AuthUser, full_name: str, phone: str, theme: str, language: str):
    user.full_name = full_name; user.phone = phone; user.theme = theme; user.language = language; db.commit(); return {"message": "Profile updated"}

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id: raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(AuthUser).filter(AuthUser.id == int(user_id)).first()
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user
