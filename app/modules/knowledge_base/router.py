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

POLICY_DIRECTORY = [
    {"title": "Business Registration Service Act", "category": "Registration", "description": "Register a business name, sole proprietorship, partnership or limited company via eCitizen / BRS. Cost from KES 1,000 for business name.", "link": "https://www.brs.go.ke/", "authority": "Business Registration Service"},
    {"title": "Tax Procedures Act - KRA PIN & Filing", "category": "Tax", "description": "All businesses must have KRA PIN. File monthly VAT by 20th and annual income tax by 30 June. Register on iTax.", "link": "https://www.kra.go.ke/", "authority": "Kenya Revenue Authority"},
    {"title": "Single Business Permit - County", "category": "Licensing", "description": "Every business needs a county Single Business Permit. Apply at your county revenue office or eCitizen county portal.", "link": "https://www.ecitizen.go.ke/", "authority": "County Government"},
    {"title": "KEBS Standards & Product Certification", "category": "Compliance", "description": "Food, cosmetics and manufactured goods need KEBS standardization mark. Apply via KEBS portal.", "link": "https://www.kebs.org/", "authority": "Kenya Bureau of Standards"},
    {"title": "Data Protection Act 2019", "category": "Data", "description": "If you collect customer phone numbers or emails, you must register as a data controller with ODPC and have a privacy notice.", "link": "https://www.odpc.go.ke/", "authority": "Office of Data Protection Commissioner"},
    {"title": "Employment Act 2007", "category": "HR", "description": "Written contracts, minimum wage by county, NHIF / NSSF / Housing Levy deductions. Keep payslips for 5 years.", "link": "https://www.labour.go.ke/", "authority": "Ministry of Labour"},
    {"title": "Food Hygiene Licence - Public Health", "category": "Food", "description": "Food businesses need food hygiene licence and medical certificates for staff every 6 months.", "link": "https://www.health.go.ke/", "authority": "Ministry of Health"},
    {"title": "NEMA Environmental Licence", "category": "Environment", "description": "Manufacturing, waste and construction projects need NEMA EIA licence before starting.", "link": "https://www.nema.go.ke/", "authority": "NEMA"},
]

GUIDE_DIRECTORY = [
    {"title": "How to Start a Business in Kenya", "category": "Starting", "description": "Step 1: Choose structure. Step 2: Register on BRS via eCitizen. Step 3: Get KRA PIN. Step 4: Get county Single Business Permit. Step 5: Open business bank / M-Pesa Till.", "link": "https://www.brs.go.ke/", "authority": "Business Registration Service"},
    {"title": "How to Get a KRA PIN and File Tax", "category": "Tax", "description": "Register on iTax, get PIN, file monthly VAT by 20th, annual income tax by 30 June. Keep receipts for 5 years.", "link": "https://www.kra.go.ke/", "authority": "Kenya Revenue Authority"},
    {"title": "How to Price Your Product", "category": "Pricing", "description": "Cost + margin + competitor check + county demand. Do not price below cost. Test price with 20 customers before printing price list.", "link": "/kb", "authority": "EvidLens"},
    {"title": "How to Get Funding", "category": "Funding", "description": "Start with SACCO / group, then Youth / Uwezo / WEF, then bank. Banks want 6 months statements. Government funds want registered group.", "link": "/reports/funding", "authority": "EvidLens"},
    {"title": "How to Export from Kenya", "category": "Export", "description": "Get KEBS mark, get export licence from regulator, check destination rules, use KEPHIS for horticulture, KEBS for food.", "link": "https://www.kepphis.org/", "authority": "KEPHIS / KEBS"},
    {"title": "How to Protect Your Business Data", "category": "Data", "description": "Register as data controller with ODPC if you collect phone numbers / emails. Have a privacy notice and do not share customer data.", "link": "https://www.odpc.go.ke/", "authority": "Office of Data Protection Commissioner"},
]

LICENCE_DIRECTORY = [
    {"title": "Single Business Permit", "category": "Licence", "description": "Required for every business. Apply at county revenue office or county eCitizen portal. Renew yearly. Fee depends on county and business size.", "link": "https://www.ecitizen.go.ke/", "authority": "County Government"},
    {"title": "Food Hygiene Licence", "category": "Licence", "description": "Required for food businesses. Staff need medical certificates every 6 months. Premises inspected by Public Health.", "link": "https://www.health.go.ke/", "authority": "Ministry of Health"},
    {"title": "KEBS Standardization Mark", "category": "Licence", "description": "Required for food, cosmetics and manufactured goods sold in Kenya. Apply via KEBS portal, product testing required.", "link": "https://www.kebs.org/", "authority": "Kenya Bureau of Standards"},
    {"title": "NEMA EIA Licence", "category": "Licence", "description": "Required for manufacturing, waste, construction projects. EIA study before starting. No licence = closure.", "link": "https://www.nema.go.ke/", "authority": "NEMA"},
    {"title": "Tourism Licence", "category": "Licence", "description": "Required for hotels, tour operators, travel agents. Apply via Tourism Regulatory Authority.", "link": "https://www.tourismauthority.go.ke/", "authority": "Tourism Regulatory Authority"},
    {"title": "Pharmacy / PPB Licence", "category": "Licence", "description": "Required for pharmacies and chemists. Apply via Pharmacy and Poisons Board. Pharmacist must be registered.", "link": "https://www.pharmacyboardkenya.org/", "authority": "Pharmacy and Poisons Board"},
    {"title": "Liquor Licence", "category": "Licence", "description": "Required to sell alcohol. Apply at county liquor licensing committee. Different classes for bar, restaurant, wholesale.", "link": "https://www.ecitizen.go.ke/", "authority": "County Government"},
    {"title": "Transport / NTSA Licence", "category": "Licence", "description": "Required for PSV, boda, logistics. Vehicle inspection, driver PSV badge, SACCO / company registration.", "link": "https://www.ntsa.go.ke/", "authority": "NTSA"},
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

def _normalize_policy(p):
    return {
        "title": p.get("title", ""),
        "name": p.get("title", ""),
        "category": p.get("category", ""),
        "description": p.get("description", ""),
        "summary": p.get("description", ""),
        "link": p.get("link", ""),
        "url": p.get("link", ""),
        "authority": p.get("authority", ""),
        "source": p.get("authority", ""),
        "is_curated": True,
        "is_live": False,
    }

def _normalize_item(p):
    return {
        "title": p.get("title", ""),
        "name": p.get("title", ""),
        "category": p.get("category", ""),
        "description": p.get("description", ""),
        "summary": p.get("description", ""),
        "link": p.get("link", ""),
        "url": p.get("link", ""),
        "authority": p.get("authority", ""),
        "source": p.get("authority", ""),
        "is_curated": True,
        "is_live": False,
    }

def _get_recent(db):
    recent = []
    try:
        rows = db.exec(select(SectorReport).order_by(desc(SectorReport.created_at)).limit(12)).all()
        recent = [{"sector": getattr(r, "sector", ""), "title": getattr(r, "title", "") or getattr(r, "sector", ""), "summary": (getattr(r, "summary", "") or "")[:180]} for r in rows]
    except Exception as e:
        logger.exception(f"kb recent failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        recent = []
    return recent

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def kb_home(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recent = _get_recent(db)
    policies = [_normalize_policy(p) for p in POLICY_DIRECTORY]
    guides = [_normalize_item(p) for p in GUIDE_DIRECTORY]
    licences = [_normalize_item(p) for p in LICENCE_DIRECTORY]
    return templates.TemplateResponse("kb.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "sectors": KENYA_SECTORS,
        "total_sectors": len(KENYA_SECTORS),
        "recent_reports": recent,
        "reports": recent,
        "policies": policies,
        "policy_list": policies,
        "policy_count": len(policies),
        "total_policies": len(policies),
        "guides": guides,
        "guide_list": guides,
        "guide_count": len(guides),
        "total_guides": len(guides),
        "licences": licences,
        "licenses": licences,
        "licence_list": licences,
        "licence_count": len(licences),
        "total_licences": len(licences),
        "items": policies + guides + licences,
        "total_reports": len(recent),
        "total": len(recent),
        "has_data": len(recent) > 0,
        "has_policies": len(policies) > 0,
        "has_guides": len(guides) > 0,
        "has_licences": len(licences) > 0,
        "is_curated": True,
        "data_source": "Curated Directory - Verify with regulator",
    })

@router.get("/policy", response_class=HTMLResponse)
@router.get("/policies", response_class=HTMLResponse)
async def policy_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recent = _get_recent(db)
    policies = [_normalize_policy(p) for p in POLICY_DIRECTORY]
    return templates.TemplateResponse("kb_policy.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "policies": policies,
        "policy_list": policies,
        "items": policies,
        "data": policies,
        "total": len(policies),
        "count": len(policies),
        "total_policies": len(policies),
        "policy_count": len(policies),
        "total_reports": len(recent),
        "recent_reports": recent,
        "has_data": len(policies) > 0,
        "has_policies": len(policies) > 0,
        "is_curated": True,
        "is_live": False,
        "data_source": "Curated Directory - Verify with regulator",
    })

@router.get("/guides", response_class=HTMLResponse)
async def guides_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recent = _get_recent(db)
    guides = [_normalize_item(p) for p in GUIDE_DIRECTORY]
    return templates.TemplateResponse("kb_guides.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "guides": guides,
        "guide_list": guides,
        "items": guides,
        "data": guides,
        "total": len(guides),
        "count": len(guides),
        "total_guides": len(guides),
        "guide_count": len(guides),
        "total_reports": len(recent),
        "recent_reports": recent,
        "has_data": len(guides) > 0,
        "has_guides": len(guides) > 0,
        "is_curated": True,
        "is_live": False,
        "data_source": "Curated Directory - Verify with regulator",
    })

@router.get("/licences", response_class=HTMLResponse)
@router.get("/licenses", response_class=HTMLResponse)
async def licences_page(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recent = _get_recent(db)
    licences = [_normalize_item(p) for p in LICENCE_DIRECTORY]
    return templates.TemplateResponse("kb_licences.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "licences": licences,
        "licenses": licences,
        "licence_list": licences,
        "items": licences,
        "data": licences,
        "total": len(licences),
        "count": len(licences),
        "total_licences": len(licences),
        "licence_count": len(licences),
        "total_reports": len(recent),
        "recent_reports": recent,
        "has_data": len(licences) > 0,
        "has_licences": len(licences) > 0,
        "is_curated": True,
        "is_live": False,
        "data_source": "Curated Directory - Verify with regulator",
    })

@router.get("/guides.json")
def guides_json():
    return {"guides": [_normalize_item(p) for p in GUIDE_DIRECTORY], "total": len(GUIDE_DIRECTORY)}

@router.get("/licences.json")
def licences_json():
    return {"licences": [_normalize_item(p) for p in LICENCE_DIRECTORY], "total": len(LICENCE_DIRECTORY)}

@router.get("/policies.json")
def policies_json():
    return {"policies": [_normalize_policy(p) for p in POLICY_DIRECTORY], "total": len(POLICY_DIRECTORY)}

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
