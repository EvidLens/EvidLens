from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index
from sqlalchemy.sql import func
from app.modules.db import Base
import enum

KENYA_SECTORS = [
    "Agriculture", "Livestock & Fisheries", "Manufacturing", "Construction & Real Estate", 
    "Mining & Quarrying", "Energy & Utilities", "ICT", "Telecommunications", "Banking", 
    "Insurance", "Microfinance & SACCOs", "Capital Markets & Investment", "Healthcare", 
    "Pharmaceuticals & Medical Supplies", "Education & Training", "Hospitality", 
    "Tourism & Travel", "Transport & Logistics", "Wholesale & Retail Trade", "Automotive", 
    "Media & Entertainment", "Creative & Digital Economy", "Professional Services", 
    "Research & Market Intelligence", "BPO", "Government & Public Administration", 
    "NGOs", "Security Services", "Environmental Services", "Water & Sanitation", 
    "FinTech", "E-commerce", "Religious Organizations", "Sports & Recreation", 
    "Beauty & Personal Care", "Fashion & Apparel", "Printing & Publishing", "Food & Beverage"
]

class SectorReport(Base):
    __tablename__ = "sector_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=True, index=True)
    
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    key_insights = Column(JSON, default=list)
    market_size_kes = Column(Float, nullable=True)
    growth_rate_percent = Column(Float, nullable=True)
    top_challenges = Column(JSON, default=list)
    opportunities = Column(JSON, default=list)
    
    data_sources = Column(JSON, default=list)
    generated_by = Column(String, default="EvidLens AI RAG")
    version = Column(String, default="v1.0")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_sector_county', 'sector', 'county'),
    )

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=True, index=True)
    
    chunk_text = Column(Text, nullable=False)
    chunk_type = Column(String, nullable=False)
    source = Column(String, nullable=False)
    
    embedding = Column(JSON, nullable=True)
    chunk_metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_chunk_sector_type', 'sector', 'chunk_type'),
    )

class FMCGInsight(Base):
    __tablename__ = "fmcg_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False, index=True)
    subcategory = Column(String, nullable=False, index=True)
    
    insight_text = Column(Text, nullable=False)
    price_trend = Column(String, nullable=True)
    demand_level = Column(String, nullable=True)
    
    county = Column(String, nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
