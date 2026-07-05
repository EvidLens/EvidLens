from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from core.db import Base

class AgentTask(Base):
    __tablename__ = "ai_agent_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String, nullable=False, index=True)  # email_draft, customer_reply, report_summary, invoice_reminder, marketing_copy
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
