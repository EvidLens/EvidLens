from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.sql import func
import enum

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
    name: str
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")
    sector: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    sub_county: Optional[str] = Field(default=None) # for Ask Lens geo
    ward: Optional[str] = Field(default=None) # for Ask Lens geo
    mpesa_paybill: Optional[str] = Field(default=None)
    kra_pin: Optional[str] = Field(default=None)
    subscription_tier: str = Field(default="free")
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

class TeamMember(SQLModel, table=True):
    __tablename__ = "team_members"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    role: UserRole = Field(default=UserRole.staff)
    can_view_reports: bool = Field(default=False)
    can_manage_inventory: bool = Field(default=False)
    can_manage_hr: bool = Field(default=False)
    can_manage_accounting: bool = Field(default=False)

class Product(SQLModel, table=True):
    __tablename__ = "business_products"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id")
    name: str
    sku: Optional[str] = Field(default=None, unique=True, index=True)
    category: Optional[str] = Field(default=None)
    buying_price: float = Field(default=0.0)
    selling_price: float = Field(default=0.0)
    stock_qty: int = Field(default=0)
    low_stock_threshold: int = Field(default=10)

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id")
    invoice_number: Optional[str] = Field(default=None, unique=True, index=True)
    customer_name: Optional[str] = Field(default=None)
    customer_phone: Optional[str] = Field(default=None)
    total_amount: Optional[float] = Field(default=None)
    status: InvoiceStatus = Field(default=InvoiceStatus.draft)
    mpesa_receipt: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

class Employee(SQLModel, table=True):
    __tablename__ = "employees"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id")
    full_name: str
    phone: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    salary_kes: float = Field(default=0.0)
    is_active: bool = Field(default=True)

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    business_id: Optional[int] = Field(default=None, foreign_key="businesses.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    action: str
    entity: Optional[str] = Field(default=None)
    entity_id: Optional[int] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    details: Optional[str] = Field(default=None)
