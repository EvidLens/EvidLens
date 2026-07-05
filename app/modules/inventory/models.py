from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from core.db import Base

class Item(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    quantity = Column(Integer, default=0)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
