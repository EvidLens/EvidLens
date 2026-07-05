from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from core.db import Base

class Campaign(Base):
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False)  # email, sms, social, ads
    budget = Column(Float, default=0.0)
    status = Column(String, default="draft")  # draft, active, paused, completed
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
