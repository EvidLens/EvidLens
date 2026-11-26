from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, desc
from pydantic import BaseModel
from typing import List, Optional
import logging

from .service import get_sector_report, search_knowledge, ingest_sector_data, generate_report_with_groq
from app.core.models import SectorReport, KnowledgeChunk, DataSource, User
from app.core.db import get_session as get_db
from app.core.guards import require_module, get_current_user

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("evidlens.kb")

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

CURATED_POLICIES = [
    {"title": "Business Registration Service Act", "category": "Registration", "description": "Register a business name, sole proprietorship, partnership or limited company via eCitizen / BRS. Cost from KES 1,000 for business name.", "link": "https://www.brs.go.ke/", "authority": "Business Registration Service"},
    {"title": "Tax Procedures Act - KRA PIN & Filing", "category": "Tax", "description": "All businesses must have KRA PIN. File monthly VAT by 20th and annual income tax by 30 June. Register on iTax.", "link": "https://www.kra.go.ke/", "authority": "Kenya Revenue Authority"},
    {"title": "Single Business Permit - County", "category": "Licensing", "description": "Every business needs a county Single Business Permit. Apply at your county revenue office or eCitizen county portal.", "link": "https://www.ecitizen.go.ke/", "authority": "County Government"},
    {"title": "KEBS Standards & Product Certification", "category": "Compliance", "description": "Food, cosmetics and manufactured goods need KEBS standardization mark. Apply via KEBS portal.", "link": "https://www.kebs.org/", "authority": "Kenya Bureau of Standards"},
    {"title": "Data Protection Act 2019", "category": "Data", "description": "If you collect customer phone numbers or emails, you must register as a data controller with ODPC and have a privacy notice.", "link": "https://www.odpc.go.ke/", "authority": "Office of Data Protection Commissioner"},
    {"title": "Employment Act 2007", "category": "HR", "description": "Written contracts, minimum wage by county, NHIF / NSSF / Housing Levy deductions. Keep payslips for 5 years.", "link": "https://www.labour.go.ke/", "authority": "Ministry of Labour"},
    {"title": "Food Hygiene Licence - Public Health", "category": "Food", "description": "Food businesses need food hygiene licence and medical certificates for staff every 6 months.", "link": "https://www.health.go.ke/", "authority": "Ministry of Health"},
    {"title": "NEMA Environmental Licence", "category": "Environment", "description": "Manufacturing, waste and construction projects need NEMA EIA licence before starting.", "link": "https://www.nema.go.ke/", "authority": "NEMA"},
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

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def kb_home(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recent = []
    try:
        rows = db.exec(select(SectorReport).order_by(desc(SectorReport.created_at)).limit(12)).all()
        recent = [{"sector": getattr(r, "sector", ""), "title": getattr(r, "title", "") or getattr(r, "sector", ""), "summary": (getattr(r, "summary", "") or "")[:180]} for r in rows]
    except Exception as e:
        logger.exception(f"kb_home recent failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        recent = []
    return templates.TemplateResponse("kb.html", {"request": request, "current_user": current_user, "user": current_user, "sectors": KENYA_SECTORS, "total_sectors": len(KENYA_SECTORS), "recent_reports": recent, "has_data": len(recent) > 0})

@router.get("/policy", response_class=HTMLResponse)
async def policy_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("kb_policy.html", {"request": request, "current_user": current_user, "user": current_user, "policies": CURATED_POLICIES, "total": len(CURATED_POLICIES), "has_data": len(CURATED_POLICIES) > 0})

@router.get("/sectors")
def list_sectors():
    return {"sectors": KENYA_SECTORS, "total": len(KENYA_SECTORS)}

@router.get("/report/{sector}", response_model=ReportResponse, dependencies=[Depends(require_module(module_number=3))])
def get_report(request: Request, sector: str, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found. Use /kb/sectors to list all sectors")
    try:
        report = get_sector_report(db, sector, county)
    except Exception as e:
        logger.exception(f"get_sector_report failed: {e}")
        report = None
    if not report:
        try:
            report = generate_report_with_groq(db, sector, county)
        except Exception as e:
            logger.exception(f"generate_report failed: {e}")
            raise HTTPException(status_code=500, detail="Report generation failed. Please try again.")
    if not report:
        raise HTTPException(status_code=404, detail="No report available for this sector yet")
    return report

@router.post("/search", dependencies=[Depends(require_module(module_number=3))])
def search_kb(request: Request, req: SearchRequest, db: Session = Depends(get_db)):
    try:
        results = search_knowledge(db, req.query, req.sector, req.county, req.top_k)
    except Exception as e:
        logger.exception(f"search_kb failed: {e}")
        return {"query": req.query, "results": [], "total": 0}
    out = []
    for r in results:
        try:
            pub = r.published_at.isoformat() if hasattr(r, "published_at") and r.published_at else None
        except Exception:
            pub = None
        out.append({"chunk_text": r.chunk_text, "sector": r.sector, "county": r.county, "source": r.source, "published_at": pub})
    return {"query": req.query, "results": out, "total": len(out)}

@router.post("/ingest", dependencies=[Depends(require_module(module_number=3))])
def ingest_data(request: Request, background_tasks: BackgroundTasks, sector: str, db: Session = Depends(get_db)):
    if sector not in KENYA_SECTORS:
        raise HTTPException(status_code=404, detail="Sector not found")
    background_tasks.add_task(ingest_sector_data, db, sector)
    return {"status": "ingestion_started", "sector": sector}
