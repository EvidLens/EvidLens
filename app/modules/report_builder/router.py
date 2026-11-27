import os
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc
from pydantic import BaseModel
from sqlalchemy import text

from app.modules.auth.dependencies import get_current_user_optional
from app.core.models import Report, ReportType, ReportFormat, ReportStatus, User, UserSubscription
from app.core.db import get_session as get_db, engine
from app.core import billing

try:
    from .service import generate_report_pdf_file
    from .service import generate_market_report_excel
except ImportError:
    from .service import generate_market_report_pdf_file as generate_report_pdf_file
    from .service import generate_market_report_excel

router = APIRouter(prefix="/reports", tags=["Report Builder"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc
logger = logging.getLogger("evidlens.reports")

ADMIN_USER_IDS = [1]
_RATE: Dict[int, list] = {}

SERIES_MAP = {
    "EXEC_BRIEF": "ExecBrief",
    "MARKET_FEASIBILITY": "MarketIntelligence",
    "INDUSTRY_OUTLOOK": "IndustryOutlook",
    "SECTOR_PULSE": "SectorPulse",
    "CONSUMER_ANALYSIS": "ConsumerInsights",
    "PRODUCT_WATCH": "ProductWatch",
    "INVESTOR_PITCH": "InvestorPitch",
    "BUSINESS_PLAN": "BusinessPlan",
    "KRA_TAX": "KRATax",
}

CURATED_FUNDERS = [
    {"name": "Equity Bank - SME Loan", "type": "Bank", "sector": "All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 5000000, "interest_rate": 14.0, "rating": 4.5, "requirements": "ID, Business registration, 6 months statements", "apply_link": "https://equitygroupholdings.com/ke/borrow/"},
    {"name": "KCB Bank - Biashara Loan", "type": "Bank", "sector": "All Sectors", "county": "All Counties", "min_amount": 100000, "max_amount": 10000000, "interest_rate": 13.5, "rating": 4.5, "requirements": "ID, KCB account, M-Pesa statements", "apply_link": "https://ke.kcbgroup.com/for-business/borrow"},
    {"name": "Co-operative Bank - MSME Loan", "type": "Bank", "sector": "Agriculture, Retail", "county": "All Counties", "min_amount": 50000, "max_amount": 3000000, "interest_rate": 14.0, "rating": 4.2, "requirements": "ID, Business registration, 6 months statements", "apply_link": "https://www.co-opbank.co.ke/business-banking/"},
    {"name": "Family Bank - Biashara Boost", "type": "Bank", "sector": "Retail, Services", "county": "All Counties", "min_amount": 30000, "max_amount": 2000000, "interest_rate": 15.0, "rating": 4.0, "requirements": "ID, Business registration", "apply_link": "https://familybank.co.ke/"},
    {"name": "Stima SACCO - Business Loan", "type": "SACCO", "sector": "All Sectors", "county": "All Counties", "min_amount": 50000, "max_amount": 5000000, "interest_rate": 12.0, "rating": 4.3, "requirements": "SACCO membership 6 months, 3x savings", "apply_link": "https://www.stima-sacco.com/"},
    {"name": "Youth Fund", "type": "Grant / Government", "sector": "Youth-led Businesses", "county": "All Counties", "min_amount": 50000, "max_amount": 500000, "interest_rate": 0.0, "rating": 4.0, "requirements": "Age 18-35, ID, group or business registration", "apply_link": "https://www.youthfund.go.ke/"},
    {"name": "Uwezo Fund", "type": "Grant / Government", "sector": "Women, Youth, PWD Groups", "county": "All Counties", "min_amount": 50000, "max_amount": 500000, "interest_rate": 0.0, "rating": 4.0, "requirements": "Registered group, ID, minutes", "apply_link": "https://www.uwezofund.go.ke/"},
    {"name": "Hustler Fund - Business", "type": "Government Loan", "sector": "Micro Businesses", "county": "All Counties", "min_amount": 500, "max_amount": 50000, "interest_rate": 8.0, "rating": 3.8, "requirements": "ID, phone, *254#", "apply_link": "https://www.hustlerfund.go.ke/"},
]

def _soft_rate_check(user_id: int):
    now = time.time()
    lst = _RATE.get(user_id, [])
    lst = [t for t in lst if now - t < 60]
    lst.append(now)
    _RATE[user_id] = lst
    if len(lst) > 20:
        raise HTTPException(status_code=429, detail="Too many reports. Wait 60 seconds and try again.")

def audit(request: Request, user_id: int, action: str, report_id: int = None):
    try:
        ip = request.client.host if request.client else "unknown"
        ua = (request.headers.get("user-agent", "") or "")[:500]
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO audit_logs (user_id, action, report_id, ip, user_agent) VALUES (:u, :a, :r, :ip, :ua)"), {"u": user_id, "a": action, "r": report_id, "ip": ip, "ua": ua})
            conn.commit()
    except Exception as e:
        logger.warning(f"audit skipped: {e}")

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
        if "EXEC" in u or "BRIEF" in u or "BUSINESS_BRIEF" in u:
            return "EXEC_BRIEF"
        if "CONSUMER" in u or "INSIGHT" in u:
            return "CONSUMER_ANALYSIS"
        if "INDUSTRY" in u or "OUTLOOK" in u:
            return "INDUSTRY_OUTLOOK"
        if "SECTOR" in u or "PULSE" in u:
            return "SECTOR_PULSE"
        if "PRODUCT" in u or "WATCH" in u:
            return "PRODUCT_WATCH"
        if "INVESTOR" in u or "PITCH" in u:
            return "INVESTOR_PITCH"
        if "KRA" in u or "TAX" in u:
            return "KRA_TAX"
        if "BUSINESS" in u or "BANK" in u or "LOAN" in u:
            return "BUSINESS_PLAN"
        return "MARKET_FEASIBILITY"

    def get_format_str(self):
        f = (self.format or "").upper()
        if "EXCEL" in f or "XLSX" in f:
            return "excel"
        return "pdf"

def _as_aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt

def get_user_plan(db: Session, user_id: int) -> str:
    try:
        sub = db.exec(select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.status == "active")).first()
        if sub is not None:
            plan_code = getattr(sub, "plan_code", None)
            if plan_code:
                return str(plan_code)
            plan_field = getattr(sub, "plan", None)
            if plan_field:
                return str(plan_field)
            return "Trial"
    except Exception as e:
        logger.warning(f"plan failed {e}")
        try:
            db.rollback()
        except Exception:
            pass
    return "Trial"

def _is_admin(user_id: int, db: Session = None) -> bool:
    if user_id in ADMIN_USER_IDS:
        return True
    if db is not None:
        try:
            u = db.exec(select(User).where(User.id == user_id)).first()
            if u is not None:
                if getattr(u, "is_admin", False):
                    return True
                if getattr(u, "role", "") in ("admin", "superadmin"):
                    return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    return False

def check_plan_access(plan_name: str, user_id: int, db: Session) -> bool:
    if _is_admin(user_id, db):
        return True
    try:
        allowed = billing.PLAN_MODULES.get(plan_name, billing.PLAN_MODULES["Trial"])
        if "Report Builder" in allowed:
            return True
        return False
    except Exception:
        return True

def resolve_user_id(request: Request, current_user=None) -> int:
    if current_user is not None and getattr(current_user, "id", None):
        return int(current_user.id)
    st = getattr(request.state, "user", None)
    if st is not None and getattr(st, "id", None):
        return int(st.id)
    raise HTTPException(status_code=401, detail="Please log in to generate or view reports")

def _get_report_or_404(db: Session, report_id: int, user_id: int):
    if _is_admin(user_id, db):
        r = db.exec(select(Report).where(Report.id == report_id)).first()
    else:
        r = db.exec(select(Report).where(Report.id == report_id, Report.user_id == user_id)).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return r

@router.get("/", response_class=HTMLResponse)
async def reports_page(request: Request, current_user=Depends(get_current_user_optional)):
    return templates.TemplateResponse("reports.html", {"request": request, "current_user": current_user, "user": current_user})

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    funders = CURATED_FUNDERS
    counties = sorted(set([f["county"] for f in funders if f.get("county")]))
    return templates.TemplateResponse("reports_funding.html", {"request": request, "current_user": current_user, "user": current_user, "companies": funders, "funders": funders, "counties": counties, "has_data": True})

@router.post("/generate")
def generate_report(request: Request, req: GenerateReportRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    user_id = resolve_user_id(request, current_user)
    _soft_rate_check(user_id)
    plan_name = get_user_plan(db, user_id)
    if not check_plan_access(plan_name, user_id, db):
        raise HTTPException(status_code=402, detail=f"Report Builder locked. Plan {plan_name} does not include Report Builder. Upgrade to Pro KES 5000")
    q = req.get_query()
    sec = req.get_sector()
    rtype_str = req.get_report_type_str()
    fmt_str = req.get_format_str()
    location_str = req.town or req.ward or req.sub_county or req.county or req.country
    tenant_id = f"user-{user_id}"
    report = Report(user_id=user_id, title=f"{rtype_str} - {q} @ {location_str}", report_type=rtype_str, format=fmt_str, query=q, sector=sec, country=req.country, county=req.county, sub_county=req.sub_county, ward=req.ward, town=req.town, status="GENERATING", is_branded=(plan_name != "Trial"))
    try:
        if hasattr(report, "tenant_id"):
            report.tenant_id = tenant_id
    except Exception:
        pass
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.exception(f"Report DB save failed: {e}")
        raise HTTPException(status_code=500, detail="Could not save report. Please try again.")
    audit(request, user_id, "REPORT_GENERATE", report.id)
    try:
        if fmt_str == "pdf":
            try:
                filepath = generate_report_pdf_file(rtype_str, q, sec, req.country, req.county, req.sub_county, req.ward, req.town, req.budget, plan_name)
            except TypeError:
                filepath = generate_report_pdf_file(q=q, sector=sec, country=req.country, county=req.county, sub_county=req.sub_county, ward=req.ward, town=req.town, budget=req.budget, plan_name=plan_name)
        else:
            result = generate_market_report_excel(db, sec, req.country, req.county, req.sub_county, req.ward, req.town, q)
            if isinstance(result, (bytes, bytearray)):
                os.makedirs("app/static/reports", exist_ok=True)
                series = SERIES_MAP.get(rtype_str, "MarketIntelligence")
                safe_q = "".join(c for c in q.replace(" ", "") if c.isalnum() or c in "-_")[:40] or "Kenya"
                geo = "".join(c for c in (location_str or "Kenya").replace(" ", "") if c.isalnum() or c in "-_")[:40] or "Kenya"
                year = datetime.now().strftime("%Y")
                filepath = f"app/static/reports/EvidLens_{series}_{safe_q}_{geo}_{year}_v1.0.xlsx"
                with open(filepath, "wb") as f:
                    f.write(bytes(result))
            else:
                filepath = result
        if not filepath:
            raise Exception("Generator returned no file")
        if not os.path.exists(str(filepath)):
            if not str(filepath).startswith("s3://"):
                raise Exception("Generator returned no file")
        report.file_path = str(filepath)
        try:
            report.file_size_kb = os.path.getsize(str(filepath)) // 1024 if os.path.exists(str(filepath)) else 0
        except Exception:
            report.file_size_kb = 0
        report.status = "READY"
        report.error_message = None
        if report.is_branded:
            report.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)
        else:
            report.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        db.add(report)
        db.commit()
        audit(request, user_id, "REPORT_READY", report.id)
        return {"report_id": report.id, "status": "READY", "plan": plan_name, "file_size_kb": report.file_size_kb, "message": f"Report {report.id} READY"}
    except Exception as e:
        logger.exception(f"Report generation failed: {e}")
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
        audit(request, user_id, "REPORT_FAILED", report.id)
        return {"report_id": report.id, "status": "FAILED", "error": "Report generation failed. Please try again."}

@router.get("/status/{report_id}")
def report_status(request: Request, report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    user_id = resolve_user_id(request, current_user)
    r = _get_report_or_404(db, report_id, user_id)
    return {"report_id": r.id, "status": str(r.status), "title": r.title, "file_path": r.file_path, "error": getattr(r, "error_message", None), "file_size_kb": r.file_size_kb, "created_at": r.created_at}

@router.get("/download/{report_id}")
def download_report(request: Request, report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    user_id = resolve_user_id(request, current_user)
    r = _get_report_or_404(db, report_id, user_id)
    if str(r.file_path or "").startswith("s3://"):
        raise HTTPException(status_code=400, detail="Report stored in S3. Local copy missing. Re-generate.")
    if r.file_path and os.path.exists(r.file_path):
        if str(r.status) != "READY":
            r.status = "READY"
            try:
                db.commit()
            except Exception:
                pass
    else:
        if str(r.status) == "FAILED":
            raise HTTPException(status_code=400, detail="Report FAILED. Please regenerate.")
        raise HTTPException(status_code=400, detail=f"Report not ready yet. Status: {r.status}. Try /reports/status/{report_id}")
    exp = _as_aware(getattr(r, "expires_at", None))
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
    audit(request, user_id, "REPORT_DOWNLOAD", report_id)
    if str(r.format) == "pdf":
        mt = "application/pdf"
    else:
        mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(r.file_path, filename=os.path.basename(r.file_path), media_type=mt)

@router.get("/list")
def list_reports(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    user_id = resolve_user_id(request, current_user)
    if _is_admin(user_id, db):
        rows = list(db.exec(select(Report).order_by(desc(Report.created_at)).limit(50)))
    else:
        rows = list(db.exec(select(Report).where(Report.user_id == user_id).order_by(desc(Report.created_at)).limit(50)))
    out = []
    for r in rows:
        out.append({"id": r.id, "title": r.title, "type": str(r.report_type), "report_type": str(r.report_type), "format": str(r.format), "status": str(r.status), "created_at": r.created_at, "downloads": r.download_count, "download_count": r.download_count, "location": r.town or r.ward or r.sub_county or r.county or r.country, "is_branded": r.is_branded, "file_path": r.file_path, "file_size_kb": r.file_size_kb, "error": getattr(r, "error_message", None), "error_message": getattr(r, "error_message", None), "query": r.query, "sector": r.sector, "county": r.county})
    return {"reports": out}

@router.delete("/{report_id}")
def delete_report(request: Request, report_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    user_id = resolve_user_id(request, current_user)
    r = _get_report_or_404(db, report_id, user_id)
    try:
        if r.file_path and os.path.exists(r.file_path):
            os.remove(r.file_path)
    except Exception as e:
        logger.warning(f"delete file failed {e}")
    audit(request, user_id, "REPORT_DELETE", report_id)
    db.delete(r)
    db.commit()
    return {"ok": True, "deleted": report_id}

@router.post("/cleanup-stuck")
def cleanup_stuck(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    user_id = resolve_user_id(request, current_user)
    if _is_admin(user_id, db):
        rows = list(db.exec(select(Report).where(Report.status == "GENERATING")))
    else:
        rows = list(db.exec(select(Report).where(Report.status == "GENERATING", Report.user_id == user_id)))
    fixed = 0
    for r in rows:
        r.status = "FAILED"
        r.error_message = "Stuck GENERATING - regenerate with new synchronous version"
        db.add(r)
        fixed = fixed + 1
    if fixed:
        db.commit()
    return {"ok": True, "fixed": fixed}

@router.get("/templates")
def get_templates():
    return {"templates": [
        {"type": "EXEC_BRIEF", "name": "Executive Intelligence Brief", "series": "EvidLens Business Briefs", "pages": "4-8", "premium": False, "audience": "C-Suite / Board"},
        {"type": "MARKET_FEASIBILITY", "name": "Market Feasibility Report - 12 Engines", "series": "EvidLens Market Intelligence", "pages": "10-15", "premium": False, "audience": "Strategy / Investment teams"},
        {"type": "INDUSTRY_OUTLOOK", "name": "Industry Outlook", "series": "EvidLens Industry Outlook", "pages": "40-120", "premium": True, "audience": "Strategy / Investment teams"},
        {"type": "SECTOR_PULSE", "name": "Sector Pulse", "series": "EvidLens Sector Pulse", "pages": "8-15", "premium": False, "audience": "Periodic monitoring"},
        {"type": "CONSUMER_ANALYSIS", "name": "Consumer Insights Report", "series": "EvidLens Consumer Insights", "pages": "20-40", "premium": True, "audience": "Strategy / Marketing"},
        {"type": "PRODUCT_WATCH", "name": "Product Watch", "series": "EvidLens Product Watch", "pages": "15-25", "premium": True, "audience": "Product teams"},
        {"type": "INVESTOR_PITCH", "name": "Investor Pitch Deck", "series": "EvidLens Business Briefs", "pages": "10-15", "premium": True, "audience": "C-Suite / Investors"},
        {"type": "BUSINESS_PLAN", "name": "Bank Loan Pack", "series": "EvidLens Business Briefs", "pages": "15-25", "premium": True, "audience": "SME / Bank"},
        {"type": "KRA_TAX", "name": "KRA Tax Report", "series": "EvidLens Business Briefs", "pages": "8-12", "premium": True, "audience": "Finance / Compliance"},
    ]}
