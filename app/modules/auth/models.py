from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.modules.database import Base
import enum

class UserRole(str, enum.Enum):
    free = "free"
    sme = "sme"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    
    sector = Column(String, nullable=True)
    county = Column(String, nullable=True)
    
    role = Column(Enum(UserRole), default=UserRole.free)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    mpesa_phone = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
