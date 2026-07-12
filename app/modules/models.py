from sqlalchemy import Column, Integer, String, Float
from app.modules.db import Base

class Sector(Base):
    __tablename__ = "sectors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class County(Base):
    __tablename__ = "counties" 
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class CoreProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    sector = Column(String)
