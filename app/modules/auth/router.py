from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from .service import create_user, login_user, get_user_by_email
from app.modules.db import get_session as get_db

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

@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(db, req)
    return {"message": "User created", "user_id": user.id}

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = login_user(db, req.email, req.password)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result
