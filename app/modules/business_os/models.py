from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.sql import func
import enum

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    staff = "staff"

class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"

class Business(SQLModel, table=True):
    __tablename__ = "businesses"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    sector: Optional[str] = Field(default=None, index=True)
    county: Optional[str] = Field(default=None, index=True)
    sub_county: Optional[str] = Field(default=None)
    ward: Optional[str] = Field(default=None)
    mpesa_paybill: Optional[str] = Field(default=None)
    kra_pin: Optional[str] = Field(default=None)
    subscription_tier: str = Field(default="free")
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})

class TeamMember(SQLModel, table=True):
    __tablename__ = "team_members"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    role: UserRole = Field(default=UserRole.staff)
    can_view_reports: bool = Field(default=False)
    can_manage_inventory: bool = Field(default=False)
    can_manage_hr: bool = Field(default=False)
    can_manage_accounting: bool = Field(default=False)

class Product(SQLModel, table=True):
    __tablename__ = "business_products"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id", index=True)
    name: str = Field(index=True)
    sku: Optional[str] = Field(default=None, index=True)
    category: Optional[str] = Field(default=None, index=True)
    buying_price: Optional[float] = Field(default=None)
    selling_price: Optional[float] = Field(default=None)
    stock_qty: int = Field(default=0)
    low_stock_threshold: int = Field(default=10)

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id", index=True)
    invoice_number: Optional[str] = Field(default=None, index=True)
    customer_name: Optional[str] = Field(default=None)
    customer_phone: Optional[str] = Field(default=None)
    total_amount: Optional[float] = Field(default=None)
    status: InvoiceStatus = Field(default=InvoiceStatus.draft)
    mpesa_receipt: Optional[str] = Field(default=None, index=True)
    paid_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})

class Employee(SQLModel, table=True):
    __tablename__ = "employees"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id", index=True)
    full_name: str = Field(index=True)
    phone: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    salary_kes: Optional[float] = Field(default=None)
    is_active: bool = Field(default=True)

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    action: str = Field(index=True)
    entity: Optional[str] = Field(default=None)
    entity_id: Optional[int] = Field(default=None)
    timestamp: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})
    details: Optional[str] = Field(default=None)
