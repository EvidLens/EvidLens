from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Index
from sqlalchemy.sql import func
from app.modules.db import Base

KENYA_SECTORS = [
    "Banks", "Microfinance Institutions", "Insurance & HMOs", "Fintechs & Mobile Money",
    "Capital Markets & Investment Banks", "SACCOs", "Retail - Supermarkets & Chains",
    "Retail - Wholesale & Distributors", "FMCG - Food & Beverage", "FMCG - Personal Care & Household",
    "Manufacturing - Food Processing", "Manufacturing - Textiles & Apparel",
    "Manufacturing - Construction Materials", "Manufacturing - Automotive & Assembly",
    "Manufacturing - Pharmaceuticals", "Manufacturing - Chemicals & Plastics",
    "Agribusiness - Crops & Farming", "Agribusiness - Livestock & Dairy",
    "Agribusiness - Horticulture & Flowers", "Agribusiness - Fisheries & Aquaculture",
    "Agribusiness - Agro-processing", "Telcos & ISPs", "Media & Broadcasting",
    "Advertising & Marketing Agencies", "PR & Communications", "Real Estate - Developers",
    "Real Estate - Agents & Brokers", "Real Estate - Property Management",
    "Construction & Infrastructure", "Architecture & Engineering", "Healthcare - Hospitals & Clinics",
    "Healthcare - Pharmacies", "Healthcare - Medical Devices & Pharma",
    "Education - Universities & Colleges", "Education - Primary & Secondary Schools",
    "Education - EdTech & Training", "Logistics & Transport", "E-Commerce & Marketplaces",
    "Hospitality - Hotels & Resorts", "Hospitality - Restaurants & QSR",
    "Tourism & Tour Operators", "Aviation & Airlines", "Maritime & Shipping",
    "Energy - Electricity Generation", "Energy - Oil & Gas", "Energy - Renewable & Solar",
    "Energy - Utilities & Water", "Mining & Minerals", "Government - National Ministries",
    "Government - County Governments", "Government - State Corporations",
    "Government - Regulatory Authorities", "Public Safety & Security", "Defense", "NGOs",
    "INGOs & UN Agencies", "Donors & Development Partners", "Foundations & Philanthropy",
    "Investors - PE & VC", "Investors - Angel & Family Offices", "Professional Services - Law",
    "Professional Services - Consulting", "Professional Services - Accounting & Audit",
    "Professional Services - HR & Recruitment", "ICT & Software Companies",
    "Data Centers & Cloud Services", "Digital Marketing & Creative", "Automotive - Dealerships",
    "Automotive - Parts & Aftermarket", "Automotive - Ride-hailing & Boda",
    "Gaming & Sports", "Entertainment & Events", "Beauty & Wellness",
    "Waste Management & Recycling", "Environmental & Climate Services"
]

class SectorReport(Base):
    __tablename__ = "sector_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(50), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    key_insights = Column(JSON, default=list)
    market_size_kes = Column(Float, nullable=True)
    growth_rate_percent = Column(Float, nullable=True)
    top_challenges = Column(JSON, default=list)
    opportunities = Column(JSON, default=list)
    data_sources = Column(JSON, default=list)
    generated_by = Column(String(100), default="EvidLens AI RAG")
    version = Column(String(20), default="v1.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_sector_county', 'sector', 'county'),
    )

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    county = Column(String(50), nullable=True, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_type = Column(String(50), nullable=False)
    source = Column(String(100), nullable=False)
    embedding = Column(JSON, nullable=True)
    chunk_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('ix_chunk_sector_type', 'sector', 'chunk_type'),
    )
