from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum
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

class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    amount_kes: float
    payment_type: str
    checkout_request_id: str = Field(unique=True, index=True)
    mpesa_receipt_number: Optional[str] = Field(default=None)
    status: PaymentStatus = Field(default=PaymentStatus.pending, sa_column=Column(SQLEnum(PaymentStatus)))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True)
    tier: SubscriptionTier = Field(default=SubscriptionTier.FREE, sa_column=Column(SQLEnum(SubscriptionTier)))
    amount_kes: float
    auto_renew: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

class MpesaTransaction(SQLModel, table=True):
    __tablename__ = "mpesa_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    checkout_request_id: str
    result_code: int
    result_desc: str
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
