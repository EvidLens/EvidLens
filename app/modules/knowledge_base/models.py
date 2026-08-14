from app.core.models import SectorReport, KnowledgeChunk
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy.sql import func

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

class KnowledgeDocument(SQLModel, table=True):
    __tablename__ = "knowledge_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=255, index=True)
    category: Optional[str] = Field(default=None, max_length=100, index=True)
    content: str
    source: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
