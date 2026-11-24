# ============================================================================
# FILE: app/modules/report_builder/router.py
# FINAL - SYNC - STR FIELDS - matches app/core/models.py
# FIX 2.5.16: naive vs aware datetime in download_report + generate_report
# ============================================================================
# Routes:
#   GET    /reports/                 -> My Reports page
#   GET    /reports/funding          -> Funding Radar page
#   POST   /reports/generate         -> Generate PDF / Excel SYNCHRONOUSLY
#   GET    /reports/status/{id}      -> Check status
#   GET    /reports/download/{id}    -> Download file
#   GET    /reports/list             -> List for table
#   DELETE /reports/{id}             -> Delete report + file
#   POST   /reports/cleanup-stuck     -> Fix old stuck GENERATING reports like #5
#   GET    /reports/templates        -> List templates
# ============================================================================

import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from sqlmodel import select
from sqlmodel import desc
from pydantic import BaseModel

from app.modules.auth.dependencies import get_current_user_optional
from .service import generate_market_report_pdf_file
from .service import generate_market_report_excel
from app.core.models import Report
from app.core.models import ReportType
from app.core.models import ReportFormat
from app.core.models import ReportStatus
from app.core.models import User
from app.core.models import UserSubscription
from app.core.db import get_session as get_db
from app.core import billing

router = APIRouter(prefix="/reports", tags=["Report Builder"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc

ADMIN_USER_IDS = [1]
ADMIN_EMAILS = [
    "noreply@evidlens.co.ke",
    "evid@example.com",
    "admin@evidlens.co.ke"
]

# ============================================================================
# REQUEST MODEL
# ============================================================================

class GenerateReportRequest(BaseModel):
    query: Optional[str] = None
    title: Optional[str] = None
    sector: Optional[str] = None
    country: str = "Kenya"
    county: Optional[str] = None
    sub_county: Optional[str] = None
    ward: Optional[str] = None
    town: Optional[str] = None
    budget: Optional[str] = None
    report_type: Optional[str] = "MARKET_FEASIBILITY"
    format: Optional[str] = "PDF"

    def get_query(self):
        if self.query is not None and self.query.strip() != "":
            return self.query.strip()
        if self.title is not None and self.title.strip() != "":
            return self.title.strip()
        return "general market analysis"

    def get_sector(self):
        if self.sector is not None and self.sector.strip() != "":
            return self.sector.strip()
        return "Agriculture"

    def get_report_type_str(self):
        u = (self.report_type or "").upper()
        if "CONSUMER" in u:
            return "CONSUMER_ANALYSIS"
        if "INVESTOR" in u:
            return "INVESTOR_PITCH"
        if "KRA" in u:
            return "KRA_TAX"
        if "BUSINESS" in u or "BANK" in u:
            return "BUSINESS_PLAN"
        return "MARKET_FEASIBILITY"

    def get_format_str(self):
        f = (self.format or "").upper()
        if "EXCEL" in f or "XLSX" in f:
            return "excel"
        return "pdf"

# ============================================================================
# HELPERS
# ============================================================================

def _as_aware(dt):
    """NEW 2.5.16: DB returns naive TIMESTAMP, datetime.now(UTC) is aware - normalize."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt

def get_user_plan(db: Session, user_id: int) -> str:
    try:
        sub = db.exec(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == "active"
            )
        ).first()
        if sub is not None:
            plan_code = getattr(sub, 'plan_code', None)
            if plan_code:
                return str(plan_code)
            plan_field = getattr(sub, 'plan', None)
            if plan_field:
                return str(plan_field)
            return "Trial"
    except Exception as e:
        print(f"plan failed {e}")
        try:
            db.rollback()
        except Exception:
            pass
    return "Trial"

def check_plan_access(plan_name: str, user_id: int, db: Session) -> bool:
    if user_id in ADMIN_USER_IDS:
        return True
    try:
        u = db.exec(select(User).where(User.id == user_id)).first()
        if u is not None:
            email = getattr(u, 'email', None)
            if email in ADMIN_EMAILS:
                return True
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    try:
        allowed = billing.PLAN_MODULES.get(plan_name, billing.PLAN_MODULES["Trial"])
        if "Report Builder" in allowed:
            return True
        return False
    except Exception:
        return True

def resolve_user_id(request: Request) -> int:
    try:
        c = request.cookies.get("user_id")
        if c is not None and str(c).isdigit():
            return int(c)
    except Exception:
        pass
    try:
        st = getattr(request.state, 'user', None)
        if st is not None and hasattr(st, 'id') and st.id:
            return int(st.id)
    except Exception:
        pass
    return 1

# ============================================================================
# PAGE 1 - GET /reports/
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def reports_page(request: Request, current_user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "current_user": current_user,
            "user": current_user
        }
    )

# ============================================================================
# PAGE 2 - GET /reports/funding
# ============================================================================

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    try:
        from app.core.models import Company
        from app.core.models import KenyaLensBusiness
        companies = []
        try:
            companies = list(db.exec(select(KenyaLensBusiness).limit(50)))
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            companies = []
        if not companies:
            try:
                companies = list(db.exec(select(Company).limit(50)))
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                companies = []
        funders = []
        for c in companies:
            funders.append(
                {
                    "name": getattr(c, 'name', 'Funder') or 'Funder',
                    "type": "Bank",
                    "sector": getattr(c, 'sector', 'Agriculture') or 'Agriculture',
                    "county": getattr(c, 'county', 'Nairobi') or 'Nairobi',
                    "min_amount": 50000,
                    "max_amount": 5000000,
                    "interest_rate": 12.5,
                    "rating": 4,
                    "requirements": "ID, Business registration, 6 months statements",
                    "apply_link": "#"
                }
            )
        counties = sorted(set([f["county"] for f in funders if f.get("county")]))
        if not counties:
            counties = [
                "Nairobi",
                "Mombasa",
                "Kisumu",
                "Nakuru",
                "Kirinyaga",
                "Kakamega",
                "Kiambu",
                "Machakos",
                "Nyeri",
                "Uasin Gishu"
            ]
        return templates.TemplateResponse(
            "reports_funding.html",
            {
                "request": request,
                "current_user": current_user,
                "user": current_user,
                "companies": companies,
                "funders": funders,
                "counties": counties
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        return templates.TemplateResponse(
            "reports_funding.html",
            {
                "request": request,
                "current_user": current_user,
                "user": current_user,
                "companies": [],
                "funders": [],
                "counties": ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Kirinyaga"]
            }
        )

# ============================================================================
# GENERATE - POST /reports/generate - SYNCHRONOUS
# ============================================================================

@router.post("/generate")
def generate_report(request: Request, req: GenerateReportRequest, db: Session = Depends(get_db)):
    user_id = resolve_user_id(request)
    plan_name = get_user_plan(db, user_id)
    if not check_plan_access(plan_name, user_id, db):
        raise HTTPException(
            status_code=402,
            detail=f"Report Builder locked. Plan {plan_name} does not include Report Builder. Upgrade to Pro KES 5000"
        )
    q = req.get_query()
    sec = req.get_sector()
    rtype_str = req.get_report_type_str()
    fmt_str = req.get_format_str()
    location_str = req.town or req.ward or req.sub_county or req.county or req.country
    report = Report(
        user_id=user_id,
        title=f"{rtype_str} - {q} @ {location_str}",
        report_type=rtype_str,
        format=fmt_str,
        query=q,
        sector=sec,
        country=req.country,
        county=req.county,
        sub_county=req.sub_county,
        ward=req.ward,
        town=req.town,
        status="GENERATING",
        is_branded=(plan_name != "Trial")
    )
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"DB save failed: {e}")
    # SYNCHRONOUS - NO BackgroundTasks - this is the fix for #5
    try:
        if fmt_str == "pdf":
            filepath = generate_market_report_pdf_file(
                q=q,
                sector=sec,
                country=req.country,
                county=req.county,
                sub_county=req.sub_county,
                ward=req.ward,
                town=req.town,
                budget=req.budget,
                plan_name=plan_name
            )
        else:
            filepath = generate_market_report_excel(
                db,
                sec,
                req.country,
                req.county,
                req.sub_county,
                req.ward,
                req.town,
                q
            )
            if isinstance(filepath, (bytes, bytearray)):
                os.makedirs("app/static/reports", exist_ok=True)
                filepath = f"app/static/reports/EvidLens_{q.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                with open(filepath, "wb") as f:
                    f.write(bytes(filepath))
        if not filepath:
            raise Exception(f"Generator returned no file: {filepath}")
        if not os.path.exists(str(filepath)):
            raise Exception(f"Generator returned no file: {filepath}")
        report.file_path = str(filepath)
        try:
            report.file_size_kb = os.path.getsize(str(filepath)) // 1024
        except Exception:
            report.file_size_kb = 0
        report.status = "READY"
        report.error_message = None
        # FIXED 2.5.16: store naive datetime so DB round-trip matches - no aware/naive crash on download
        if report.is_branded:
            report.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)
        else:
            report.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        db.add(report)
        db.commit()
        return {
            "report_id": report.id,
            "status": "READY",
            "plan": plan_name,
            "file_size_kb": report.file_size_kb,
            "message": f"Report {report.id} READY"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            report.status = "FAILED"
            report.error_message = str(e)[:1000]
            db.add(report)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        return {
            "report_id": report.id,
            "status": "FAILED",
            "error": str(e)[:500]
        }

# ============================================================================
# STATUS - GET /reports/status/{id}
# ============================================================================

@router.get("/status/{report_id}")
def report_status(report_id: int, db: Session = Depends(get_db)):
    r = db.exec(select(Report).where(Report.id == report_id)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report_id": r.id,
        "status": str(r.status),
        "title": r.title,
        "file_path": r.file_path,
        "error": getattr(r, 'error_message', None),
        "file_size_kb": r.file_size_kb,
        "created_at": r.created_at
    }

# ============================================================================
# DOWNLOAD - GET /reports/download/{id} - FIXED naive vs aware
# ============================================================================

@router.get("/download/{report_id}")
def download_report(report_id: int, db: Session = Depends(get_db)):
    r = db.exec(select(Report).where(Report.id == report_id)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    if r.file_path and os.path.exists(r.file_path):
        if str(r.status) != "READY":
            r.status = "READY"
            try:
                db.commit()
            except Exception:
                pass
    else:
        if str(r.status) == "FAILED":
            raise HTTPException(
                status_code=400,
                detail=f"Report FAILED: {getattr(r, 'error_message', None) or 'Generator error'}. Regenerate."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Report not ready yet. Status: {r.status}. Try /reports/status/{report_id}"
        )
    # FIXED 2.5.16: normalize expires_at to aware before comparing - was crashing on old reports
    exp = _as_aware(getattr(r, 'expires_at', None))
    if exp is not None and exp < datetime.now(UTC):
        r.status = "EXPIRED"
        try:
            db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=410, detail="Report expired")
    try:
        r.download_count = (r.download_count or 0) + 1
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    if str(r.format) == "pdf":
        mt = "application/pdf"
    else:
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        r.file_path,
        filename=os.path.basename(r.file_path),
        media_type=mt
    )

# ============================================================================
# LIST - GET /reports/list
# ============================================================================

@router.get("/list")
def list_reports(db: Session = Depends(get_db)):
    rows = list(db.exec(select(Report).order_by(desc(Report.created_at)).limit(50)))
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "title": r.title,
                "type": str(r.report_type),
                "report_type": str(r.report_type),
                "format": str(r.format),
                "status": str(r.status),
                "created_at": r.created_at,
                "downloads": r.download_count,
                "download_count": r.download_count,
                "location": r.town or r.ward or r.sub_county or r.county or r.country,
                "is_branded": r.is_branded,
                "file_path": r.file_path,
                "file_size_kb": r.file_size_kb,
                "error": getattr(r, 'error_message', None),
                "error_message": getattr(r, 'error_message', None),
                "query": r.query,
                "sector": r.sector,
                "county": r.county
            }
        )
    return {"reports": out}

# ============================================================================
# DELETE - DELETE /reports/{id}
# ============================================================================

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    r = db.exec(select(Report).where(Report.id == report_id)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        if r.file_path and os.path.exists(r.file_path):
            os.remove(r.file_path)
    except Exception as e:
        print(f"delete file failed {e}")
    db.delete(r)
    db.commit()
    return {"ok": True, "deleted": report_id}

# ============================================================================
# CLEANUP - POST /reports/cleanup-stuck
# ============================================================================

@router.post("/cleanup-stuck")
def cleanup_stuck(db: Session = Depends(get_db)):
    rows = list(db.exec(select(Report).where(Report.status == "GENERATING")))
    fixed = 0
    for r in rows:
        r.status = "FAILED"
        r.error_message = "Stuck GENERATING from old BackgroundTasks version - regenerate with new synchronous version"
        db.add(r)
        fixed = fixed + 1
    if fixed:
        db.commit()
    return {"ok": True, "fixed": fixed}

# ============================================================================
# TEMPLATES - GET /reports/templates
# ============================================================================

@router.get("/templates")
def get_templates():
    return {
        "templates": [
            {"type": "MARKET_FEASIBILITY", "name": "Market Feasibility Report - 12 Engines", "premium": False},
            {"type": "CONSUMER_ANALYSIS", "name": "Consumer Analysis", "premium": False},
            {"type": "INVESTOR_PITCH", "name": "Investor Pitch Deck", "premium": True},
            {"type": "KRA_TAX", "name": "KRA Tax Report", "premium": True},
            {"type": "BUSINESS_PLAN", "name": "Bank Loan Pack", "premium": True}
        ]
    }
