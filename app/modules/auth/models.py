from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.sql import func
import enum

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class AuthUser(SQLModel, table=True):
    __tablename__ = "auth_users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = Field(default=None, unique=True, index=True)
    full_name: str
    hashed_password: str
    avatar_url: Optional[str] = Field(default=None)
    plan: str = Field(default="BASIC")
    credits: int = Field(default=0)
    email_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None, unique=True)
    reset_token: Optional[str] = Field(default=None, unique=True)
    reset_token_expires: Optional[datetime] = Field(default=None)
    sector: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    two_fa_enabled: bool = Field(default=False)
    theme: str = Field(default="light")
    language: str = Field(default="en")
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
