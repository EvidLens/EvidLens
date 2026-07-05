from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)  # mpesa, card, bank, cash
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    transaction_ref = Column(String, unique=True, nullable=False, index=True)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
