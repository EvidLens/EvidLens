from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.modules.db import Base
import enum

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    SME_STARTER = "sme_starter"
    SME_PRO = "sme_pro"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount_kes = Column(Float)
    payment_type = Column(String)
    checkout_request_id = Column(String, unique=True, index=True)
    mpesa_receipt_number = Column(String, nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    amount_kes = Column(Float)
    auto_renew = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MpesaTransaction(Base):
    __tablename__ = "mpesa_transactions"
    id = Column(Integer, primary_key=True, index=True)
    checkout_request_id = Column(String)
    result_code = Column(Integer)
    result_desc = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
