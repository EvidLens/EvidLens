from app.core.models import SectorReport, KnowledgeChunk
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.sql import func

__all__ = ["SectorReport", "KnowledgeChunk", "KENYA_SECTORS", "KnowledgeDocument", "normalize_sector", "is_valid_sector"]

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

KENYA_SECTORS = [
    "Banks",
    "Microfinance Institutions",
    "Insurance & HMOs",
    "Fintechs & Mobile Money",
    "Capital Markets & Investment Banks",
    "SACCOs",
    "Retail - Supermarkets & Chains",
    "Retail - Wholesale & Distributors",
    "FMCG - Food & Beverage",
    "FMCG - Personal Care & Household",
    "Manufacturing - Food Processing",
    "Manufacturing - Textiles & Apparel",
    "Manufacturing - Construction Materials",
    "Manufacturing - Automotive & Assembly",
    "Manufacturing - Pharmaceuticals",
    "Manufacturing - Chemicals & Plastics",
    "Agribusiness - Crops & Farming",
    "Agribusiness - Livestock & Dairy",
    "Agribusiness - Horticulture & Flowers",
    "Agribusiness - Fisheries & Aquaculture",
    "Agribusiness - Agro-processing",
    "Telcos & ISPs",
    "Media & Broadcasting",
    "Advertising & Marketing Agencies",
    "PR & Communications",
    "Real Estate - Developers",
    "Real Estate - Agents & Brokers",
    "Real Estate - Property Management",
    "Construction & Infrastructure",
    "Architecture & Engineering",
    "Healthcare - Hospitals & Clinics",
    "Healthcare - Pharmacies",
    "Healthcare - Medical Devices & Pharma",
    "Education - Universities & Colleges",
    "Education - Primary & Secondary Schools",
    "Education - EdTech & Training",
    "Logistics & Transport",
    "E-Commerce & Marketplaces",
    "Hospitality - Hotels & Resorts",
    "Hospitality - Restaurants & QSR",
    "Tourism & Tour Operators",
    "Aviation & Airlines",
    "Maritime & Shipping",
    "Energy - Electricity Generation",
    "Energy - Oil & Gas",
    "Energy - Renewable & Solar",
    "Energy - Utilities & Water",
    "Mining & Minerals",
    "Government - National Ministries",
    "Government - County Governments",
    "Government - State Corporations",
    "Government - Regulatory Authorities",
    "Public Safety & Security",
    "Defense",
    "NGOs",
    "INGOs & UN Agencies",
    "Donors & Development Partners",
    "Foundations & Philanthropy",
    "Investors - PE & VC",
    "Investors - Angel & Family Offices",
    "Professional Services - Law",
    "Professional Services - Consulting",
    "Professional Services - Accounting & Audit",
    "Professional Services - HR & Recruitment",
    "ICT & Software Companies",
    "Data Centers & Cloud Services",
    "Digital Marketing & Creative",
    "Automotive - Dealerships",
    "Automotive - Parts & Aftermarket",
    "Automotive - Ride-hailing & Boda",
    "Gaming & Sports",
    "Entertainment & Events",
    "Beauty & Wellness",
    "Waste Management & Recycling",
    "Environmental & Climate Services"
]

SECTOR_ALIASES = {
    "bank": "Banks",
    "banks": "Banks",
    "insurance": "Insurance & HMOs",
    "sacco": "SACCOs",
    "saccos": "SACCOs",
    "agribusiness": "Agribusiness - Crops & Farming",
    "farming": "Agribusiness - Crops & Farming",
    "retail": "Retail - Supermarkets & Chains",
    "ecommerce": "E-Commerce & Marketplaces",
    "e-commerce": "E-Commerce & Marketplaces",
    "tourism": "Tourism & Tour Operators",
    "hospitality": "Hospitality - Hotels & Resorts",
    "health": "Healthcare - Hospitals & Clinics",
    "healthcare": "Healthcare - Hospitals & Clinics",
    "education": "Education - Universities & Colleges",
    "energy": "Energy - Electricity Generation",
    "solar": "Energy - Renewable & Solar",
    "fintech": "Fintechs & Mobile Money",
    "telco": "Telcos & ISPs",
}

def normalize_sector(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    key = str(name).strip().lower()
    if key in SECTOR_ALIASES:
        return SECTOR_ALIASES[key]
    for s in KENYA_SECTORS:
        if s.lower() == key:
            return s
    return str(name).strip()

def is_valid_sector(name: str) -> bool:
    return normalize_sector(name) in KENYA_SECTORS

class KnowledgeDocument(SQLModel, table=True):
    __tablename__ = "knowledge_documents"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255, index=True)
    category: Optional[str] = Field(default=None, max_length=100, index=True)
    sector: Optional[str] = Field(default=None, max_length=100, index=True)
    county: Optional[str] = Field(default=None, max_length=100, index=True)
    content: str = Field(default="")
    source: Optional[str] = Field(default=None, max_length=255)
    source_url: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})
