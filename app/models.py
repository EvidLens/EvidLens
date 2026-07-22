from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")

class LensBusiness(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    tenant_id: int = Field(foreign_key="tenant.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensSurvey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    business_id: int = Field(foreign_key="lensbusiness.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LensResponse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    survey_id: int = Field(foreign_key="lenssurvey.id")
    data: str # store json as string
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
