from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.sql import func
import enum

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class AuthUser(SQLModel, table=True):
    __tablename__ = "auth_user"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    phone: Optional[str] = Field(default=None, unique=True, index=True, max_length=20)
    full_name: str = Field(nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    plan: str = Field(default="BASIC", index=True, max_length=20)
    credits: int = Field(default=0)
    email_verified: bool = Field(default=False, index=True)
    verification_token: Optional[str] = Field(default=None, index=True, max_length=255)
    reset_token: Optional[str] = Field(default=None, index=True, max_length=255)
    reset_token_expires: Optional[datetime] = Field(default=None)
    sector: Optional[str] = Field(default=None, index=True, max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=100)
    role: UserRole = Field(default=UserRole.USER, index=True)
    is_active: bool = Field(default=True, index=True)
    two_fa_enabled: bool = Field(default=False)
    theme: str = Field(default="light", max_length=20)
    language: str = Field(default="en", max_length=10)
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})
    last_login: Optional[datetime] = Field(default=None)
