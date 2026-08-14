from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, desc
from pydantic import BaseModel
from typing import List, Optional
from.service import get_sector_report, search_knowledge, ingest_sector_data, generate_report_with_groq
from app.core.models import SectorReport, KnowledgeChunk, DataSource
from app.core.db import get_session as get_db
from app.core.guards import require_module

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])
templates = Jinja2Templates(directory="app/templates")

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

@router.get("/policy", response_class=HTMLResponse)
async def policy_page(request: Request):
    return templates.TemplateResponse("kb_policy.html", {"request": request})

@router.get("/sectors")
def list_sectors():
    return {"sectors": KENYA_SECTORS, "total": len(KENYA_SECTORS)}

@router.get("/report/{sector}", response_model=ReportResponse)
@require_module(module_number=3)
def get_report(request: Request, sector: str, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found. Use /kb/sectors to list all 75")

    report = get_sector_report(db, sector, county)
    if not report:
        report = generate_report_with_groq(db, sector, county)

    return report

@router.post("/search")
@require_module(module_number=3)
def search_kb(request: Request, req: SearchRequest, db: Session = Depends(get_db)):
    results = search_knowledge(db, req.query, req.sector, req.county, req.top_k)
    return {
        "query": req.query,
        "results": [
            {
                "chunk_text": r.chunk_text,
                "sector": r.sector,
                "county": r.county,
                "source": r.source,
                "published_at": r.published_at.isoformat() if hasattr(r, 'published_at') and r.published_at else None
            } for r in results
        ]
    }

@router.post("/ingest")
@require_module(module_number=3)
def ingest_data(request: Request, background_tasks: BackgroundTasks, sector: str, db: Session = Depends(get_db)):
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found")
    background_tasks.add_task(ingest_sector_data, db, sector)
    return {"status": "ingestion_started", "sector": sector}
