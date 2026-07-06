from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from modules.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True) # For M-Pesa verification
    hashed_password = Column(String, nullable=False)
    
    # EvidLens Specific: Zero Setup Fields
    sector = Column(String, nullable=True, index=True) # From your 36 sectors list
    county = Column(String, nullable=True, index=True) # From 47 Counties
    
    # Monetization + RBAC
    plan = Column(String, default="free") # free, sme_starter, sme_pro, business, enterprise
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False) # Phone/Email verified for M-Pesa
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
