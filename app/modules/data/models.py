from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.modules.database import Base

class DataSource(Base):
    __tablename__ = "data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(100), nullable=True)
    url = Column(String(500), nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
