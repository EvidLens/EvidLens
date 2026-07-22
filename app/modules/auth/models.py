from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.sql import func
import enum

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    STAFF = "STAFF"

class User(SQLModel, table=True):
    __tablename__ = "auth_users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = Field(default=None, unique=True, index=True)
    full_name: str
    hashed_password: str
    sector: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
