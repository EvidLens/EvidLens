from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.db import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    invoice_number = Column(String, unique=True, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
