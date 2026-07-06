from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.modules.database import Base

class ReportType(str, enum.Enum):
    MARKET_FEASIBILITY = "market_feasibility"
    CONSUMER_ANALYSIS = "consumer_analysis"
    BUSINESS_PLAN = "business_plan"
    KRA_TAX = "kra_tax"
    COMPETITOR_TRACKER = "competitor_tracker"
    INVESTOR_PITCH = "investor_pitch"

class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"

class ReportStatus(str, enum.Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Report Details
    title = Column(String, nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    format = Column(Enum(ReportFormat), default=ReportFormat.PDF)
    status = Column(Enum(ReportStatus), default=ReportStatus.GENERATING)
    
    # Context used to generate
    query = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    county = Column(String, nullable=True)
    
    # Files
    file_path = Column(String, nullable=True) # /tmp/ or Cloudflare R2 URL
    file_size_kb = Column(Integer, nullable=True)
    download_count = Column(Integer, default=0)
    
    # Branding + KRA
    is_branded = Column(Boolean, default=False) # Premium: logo + custom colors
    kra_compliant = Column(Boolean, default=True)
    metadata = Column(JSON, default=dict) # Stores raw data used for audit
    
    # Monetization
    payment_id = Column(Integer, nullable=True) # Link to payments table for KSH 500 reports
    is_auto_weekly = Column(Boolean, default=False) # SME Pro+ feature
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True) # Free reports expire in 7 days

class ReportTemplate(Base):
    __tablename__ = "report_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    
    # Template config
    sections = Column(JSON, default=list) # ["executive_summary", "market_metrics", "risk"]
    is_premium = Column(Boolean, default=False) # Pitch Deck, Bank Loan Pack are premium
    
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReportShare(Base):
    __tablename__ = "report_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    shared_by_user_id = Column(Integer, nullable=False)
    
    share_type = Column(String, default="link") # link, email, whatsapp
    recipient = Column(String, nullable=True) # email or phone
    access_token = Column(String, unique=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
