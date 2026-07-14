from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import get_sector_report, search_knowledge, ingest_sector_data, generate_report_with_groq
from.models import SectorReport, KnowledgeChunk
from app.modules.data.models import DataSource
from app.modules.db import get_db

router = APIRouter()

# Use all 75 sectors from your pricing doc
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

class ReportResponse(BaseModel):
    sector: str
    county: Optional[str]
    title: str
    summary: str
    key_insights: List[str]
    market_size_kes: Optional[float]
    growth_rate_percent: Optional[float]

class SearchRequest(BaseModel):
    query: str
    sector: Optional[str] = None
    county: Optional[str] = None
    top_k: int = 5

@router.get("/sectors")
def list_sectors():
    """Return all 75 Kenya sectors. Used for Zero Setup dropdown"""
    return {"sectors": KENYA_SECTORS, "total": len(KENYA_SECTORS)}

@router.get("/report/{sector}", response_model=ReportResponse)
def get_report(
    sector: str,
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get prebuilt industry report. Auto-loads on signup. Auto-generates if missing"""
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found. Use /sectors to list all 75")

    report = get_sector_report(db, sector, county)
    if not report:
        # Auto-generate if missing using Groq + data layer
        report = generate_report_with_groq(db, sector, county)

    return report

@router.post("/search")
def search_kb(request: SearchRequest, db: Session = Depends(get_db)):
    """RAG search for Lens chatbot and AI Insight Generator across all 9 lanes"""
    results = search_knowledge(db, request.query, request.sector, request.county, request.top_k)
    return {
        "query": request.query,
        "results": [
            {
                "chunk_text": r.chunk_text,
                "sector": r.sector,
                "county": r.county,
                "source": r.source
            } for r in results
        ]
    }

@router.post("/ingest")
def ingest_data(background_tasks: BackgroundTasks, sector: str, db: Session = Depends(get_db)):
    """Admin endpoint to trigger data refresh for a sector"""
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found")
    background_tasks.add_task(ingest_sector_data, db, sector)
    return {"status": "ingestion_started", "sector": sector}
