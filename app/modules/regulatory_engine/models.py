from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, UTC

class Regulation(SQLModel, table=True):
    __tablename__ = "regulation"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    sector: str = Field(index=True)
    regulator: str = Field(index=True) # CBK, KRA, NEMA, etc
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str
    document_url: Optional[str] = None
    county: Optional[str] = None

class ComplianceDeadline(SQLModel, table=True):
    __tablename__ = "compliance_deadline"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    sector: str = Field(index=True)
    regulator: str = Field(index=True)
    deadline: datetime
    penalty: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending" # pending, completed, overdue
