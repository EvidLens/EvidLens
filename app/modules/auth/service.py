from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .models import User, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, req):
    hashed_pw = hash_password(req.password)
    db_user = User(
        email=req.email,
        phone=req.phone,
        hashed_password=hashed_pw,
        full_name=req.full_name,
        sector=req.sector,
        county=req.county,
        role=UserRole.USER,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def login_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return {"error": "Invalid credentials"}
    if not verify_password(password, user.hashed_password):
        return {"error": "Invalid credentials"}
    return {"message": "Login successful", "user_id": user.id, "role": user.role}
