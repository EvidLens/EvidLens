from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, JSON, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.modules.database import Base

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    SME_STARTER = "sme_starter"  # 500 KES/report
    SME_PRO = "sme_pro"          # 2000 KES/mo
    PROFESSIONAL = "professional" # 5000 KES/mo
    BUSINESS = "business"        # 15000 KES/mo
    ENTERPRISE = "enterprise"    # 40000+ KES/mo

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # M-Pesa Details
    phone_number = Column(String, nullable=False)
    amount_kes = Column(Float, nullable=False)
    checkout_request_id = Column(String, unique=True, nullable=True, index=True)
    mpesa_receipt_number = Column(String, nullable=True, index=True)
    
    # What was paid for
    payment_type = Column(String, nullable=False) # "subscription", "report", "api_credits"
    reference_id = Column(Integer, nullable=True) # report_id or subscription_id
    
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    description = Column(String, nullable=True)
    
    metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    __table_args__ = (
        Index('ix_payment_user_status', 'user_id', 'status'),
    )

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    status = Column(String, default="active") # active, cancelled, expired
    
    # Limits based on tier
    searches_left = Column(Integer, default=3)
    ai_credits_left = Column(Integer, default=10)
    reports_left = Column(Integer, default=1)
    api_calls_left = Column(Integer, default=0)
    
    # Billing
    current_period_start = Column(DateTime(timezone=True), server_default=func.now())
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=False)
    
    last_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class MpesaTransaction(Base):
    __tablename__ = "mpesa_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    
    transaction_type = Column(String, nullable=False) # STKPush, C2B, B2C
    business_short_code = Column(String, nullable=True)
    trans_id = Column(String, unique=True, nullable=False, index=True)
    
    first_name = Column(String, nullable=True)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    raw_callback = Column(JSON, default=dict)
    
    received_at = Column(DateTime(timezone=True), server_default=func.now())
