from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.modules.database import Base
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

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    sector = Column(String, nullable=True)
    county = Column(String, nullable=True)
    mpesa_paybill = Column(String, nullable=True)
    kra_pin = Column(String, nullable=True)
    subscription_tier = Column(String, default="free")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    team = relationship("TeamMember", back_populates="business")
    products = relationship("Product", back_populates="business")
    invoices = relationship("Invoice", back_populates="business")
    employees = relationship("Employee", back_populates="business")

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(Enum(UserRole), default=UserRole.staff)
    can_view_reports = Column(Boolean, default=False)
    can_manage_inventory = Column(Boolean, default=False)
    can_manage_hr = Column(Boolean, default=False)
    can_manage_accounting = Column(Boolean, default=False)
    
    business = relationship("Business", back_populates="team")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String, nullable=False)
    sku = Column(String, unique=True, index=True)
    category = Column(String, nullable=True)
    buying_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    
    business = relationship("Business", back_populates="products")

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    invoice_number = Column(String, unique=True, index=True)
    customer_name = Column(String)
    customer_phone = Column(String)
    total_amount = Column(Float)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.draft)
    mpesa_receipt = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    business = relationship("Business", back_populates="invoices")

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    full_name = Column(String, nullable=False)
    phone = Column(String)
    role = Column(String)
    salary_kes = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    
    business = relationship("Business", back_populates="employees")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    entity = Column(String)
    entity_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(Text, nullable=True)
