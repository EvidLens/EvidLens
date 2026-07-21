from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Column, JSON, Index
from sqlalchemy.sql import func

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

class SectorReport(SQLModel, table=True):
    __tablename__ = "sector_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=50)
    title: str = Field(max_length=255)
    summary: str
    key_insights: List[dict] = Field(default=[], sa_column=Column(JSON))
    market_size_kes: Optional[float] = Field(default=None)
    growth_rate_percent: Optional[float] = Field(default=None)
    top_challenges: List[dict] = Field(default=[], sa_column=Column(JSON))
    opportunities: List[dict] = Field(default=[], sa_column=Column(JSON))
    data_sources: List[dict] = Field(default=[], sa_column=Column(JSON))
    generated_by: str = Field(default="EvidLens AI RAG", max_length=100)
    version: str = Field(default="v1.0", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (
        Index('ix_sector_county', 'sector', 'county'),
    )

class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=50)
    chunk_text: str
    chunk_type: str = Field(max_length=50)
    source: str = Field(max_length=100)
    embedding: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    chunk_metadata: Dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

    __table_args__ = (
        Index('ix_chunk_sector_type', 'sector', 'chunk_type'),
    )
