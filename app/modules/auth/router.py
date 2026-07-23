from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel import Session
from pydantic import BaseModel, EmailStr
from.service import *
from.models import AuthUser
from app.modules.database import get_session as get_db
import secrets

router = APIRouter()

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
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    token = secrets.token_urlsafe(32)
    create_user(db, req, token)
    return {"message": "Check email to verify"}

@router.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    user = verify_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    return RedirectResponse(url="/login")

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(db, req.email, req.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    response = JSONResponse(content=result)
    response.set_cookie(key="user_id", value=str(result["user_id"]), httponly=True)
    return response

@router.post("/forgot-password")
def forgot(req: ForgotRequest, db: Session = Depends(get_db)):
    return request_password_reset(db, req.email)

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
    response.delete_cookie("user_id")
    return response
