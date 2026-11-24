from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta, timezone
import httpx

from app.modules.auth.dependencies import get_current_user_optional
from .service import generate_market_report_pdf_file, generate_market_report_excel
from app.modules.report_builder.models import Report, ReportType, ReportFormat, ReportStatus
from app.core.db import get_session as get_db
from app.core.models import UserSubscription
from app.core import billing

router = APIRouter(prefix="/reports", tags=["Report Builder"])
templates = Jinja2Templates(directory="app/templates")
GROQ_KEY = os.getenv("GROQ_API_KEY")
UTC = timezone.utc

ADMIN_USER_IDS = [1]
ADMIN_EMAILS = ["noreply@evidlens.co.ke", "evid@example.com", "admin@evidlens.co.ke"]

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
        return self.query or self.title or "general market analysis"
    def get_sector(self):
        return self.sector or "Agriculture"
    def get_report_type(self):
        try:
            if isinstance(self.report_type, str):
                upper = self.report_type.upper()
                if "MARKET" in upper: return ReportType.MARKET_FEASIBILITY
                if "CONSUMER" in upper: return ReportType.CONSUMER_ANALYSIS
                if "INVESTOR" in upper: return ReportType.INVESTOR_PITCH
                if "KRA" in upper: return ReportType.KRA_TAX
                if "BUSINESS" in upper or "BANK" in upper: return ReportType.BUSINESS_PLAN
                return ReportType.MARKET_FEASIBILITY
            return self.report_type
        except:
            return ReportType.MARKET_FEASIBILITY
    def get_format(self):
        try:
            if isinstance(self.format, str):
                if "PDF" in self.format.upper(): return ReportFormat.PDF
                if "EXCEL" in self.format.upper() or "XLSX" in self.format.upper(): return ReportFormat.EXCEL
                return ReportFormat.PDF
            return self.format
        except:
            return ReportFormat.PDF

@router.get("/", response_class=HTMLResponse)
async def reports_page(request: Request, current_user = Depends(get_current_user_optional)):
    return templates.TemplateResponse("reports.html", {"request": request, "current_user": current_user, "user": current_user})

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user_optional)):
    try:
        from app.core.models import Company
        from app.core.models import KenyaLensBusiness
        try:
            companies = list(db.exec(select(KenyaLensBusiness).limit(50)))
        except:
            db.rollback()
            companies = []
        if not companies:
            try:
                companies = list(db.exec(select(Company).limit(50)))
            except:
                db.rollback()
                companies = []
        for tmpl_name in ["reports_funding.html", "funding.html", "reports/funding.html", "business_os.html", "dashboard.html"]:
            try:
                return templates.TemplateResponse(tmpl_name, {"request": request, "current_user": current_user, "user": current_user, "companies": companies, "data": {"companies": companies, "count": len(companies)}})
            except Exception:
                continue
        return HTMLResponse(f"<h1>Funding Radar - {len(companies)} companies</h1><p>Template missing but data OK</p>")
    except Exception as e:
        import traceback
        traceback.print_exc()
        try: db.rollback()
        except: pass
        return templates.TemplateResponse("dashboard.html", {"request": request, "current_user": current_user, "data": {"modules": [], "error": str(e)}})

def get_user_plan(db: Session, user_id: int) -> str:
    try:
        stmt = select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.status == "active")
        sub = db.exec(stmt).first()
        if sub:
            return getattr(sub, 'plan_code', 'Trial')
    except:
        pass
    return "Trial"

def check_plan_access(plan_name: str, required_module: str = "Report Builder", user_id: int = None, db: Session = None) -> bool:
    if user_id in ADMIN_USER_IDS:
        return True
    if db is not None and user_id is not None:
        try:
            from app.core.models import User
            u = db.exec(select(User).where(User.id == user_id)).first()
            if u and getattr(u, 'email', None) in ADMIN_EMAILS:
                return True
        except:
            pass
    allowed = billing.PLAN_MODULES.get(plan_name, billing.PLAN_MODULES["Trial"])
    return required_module in allowed

@router.post("/generate")
def generate_report(request: Request, req: GenerateReportRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # FIX: use cookie / session user, not request.state which is often empty
    user_id = None
    try:
        uid_cookie = request.cookies.get("user_id")
        if uid_cookie and str(uid_cookie).isdigit():
            user_id = int(uid_cookie)
    except: pass
    if not user_id:
        st_user = getattr(request.state, 'user', None)
        if st_user:
            user_id = getattr(st_user, 'id', 1) if hasattr(st_user, 'id') else 1
    if not user_id:
        user_id = 1
    plan_name = get_user_plan(db, user_id)
    if not check_plan_access(plan_name, "Report Builder", user_id, db):
        raise HTTPException(status_code=402, detail=f"Report Builder locked. Your plan {plan_name} does not include Report Builder. Upgrade to Pro KES 5000 - https://app.evidlens.co.ke/api/billing/plans")
    q = req.get_query()
    sec = req.get_sector()
    rtype = req.get_report_type()
    fmt = req.get_format()
    location_str = req.town or req.ward or req.sub_county or req.county or req.country
    report = Report(
        user_id=user_id,
        title=f"{rtype.value} - {q} @ {location_str}",
        report_type=rtype,
        format=fmt,
        query=q,
        sector=sec,
        country=req.country,
        county=req.county,
        sub_county=req.sub_county,
        ward=req.ward,
        town=req.town,
        status=ReportStatus.GENERATING,
        is_branded=plan_name != "Trial"
    )
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception as e:
        db.rollback()
        print(f"[REPORT SAVE ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"DB save failed: {str(e)}")
    background_tasks.add_task(process_report_generation, report.id, req, plan_name)
    return {"report_id": report.id, "status": "generating", "plan": plan_name, "message": f"Report {report.id} generating with 12 engines LIVE for {q} @ {location_str}. Poll /reports/status/{report.id} or /reports/list"}

def process_report_generation(report_id: int, req: GenerateReportRequest, plan_name: str = "Pro"):
    from app.core.db import engine as bg_engine
    from sqlmodel import Session as BgSession
    with BgSession(bg_engine) as db:
        report = db.exec(select(Report).where(Report.id == report_id)).first()
        if not report:
            return
        try:
            if req.get_format() == ReportFormat.PDF:
                filepath = generate_market_report_pdf_file(
                    q=req.get_query(),
                    sector=req.get_sector(),
                    country=req.country,
                    county=req.county,
                    sub_county=req.sub_county,
                    ward=req.ward,
                    town=req.town,
                    budget=req.budget,
                    plan_name=plan_name
                )
                # service may return bytes or path
                if isinstance(filepath, (bytes, bytearray)):
                    os.makedirs("app/static/reports", exist_ok=True)
                    filepath = f"app/static/reports/EvidLens_{req.get_query()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    with open(filepath, "wb") as f:
                        f.write(bytes(filepath))
            else:
                result = generate_market_report_excel(db, req.get_sector(), req.country, req.county, req.sub_county, req.ward, req.town, req.get_query())
                # FIX: old code threw away real Excel bytes and wrote empty file
                if isinstance(result, (bytes, bytearray)):
                    os.makedirs("app/static/reports", exist_ok=True)
                    filepath = f"app/static/reports/EvidLens_{req.get_query()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                    with open(filepath, "wb") as f:
                        f.write(bytes(result))
                elif isinstance(result, str) and result:
                    filepath = result
                else:
                    filepath = result
            # If service returned None / empty, fail clearly instead of stuck
            if not filepath or (isinstance(filepath, str) and not os.path.exists(filepath)):
                raise Exception(f"Generator returned no file: {filepath}")
            report.file_path = filepath if isinstance(filepath, str) else str(filepath)
            try:
                report.file_size_kb = os.path.getsize(report.file_path) // 1024
            except:
                report.file_size_kb = 0
            report.status = ReportStatus.READY
            report.error_message = None
            report.expires_at = datetime.now(UTC) + timedelta(days=30 if report.is_branded else 7)
            db.add(report)
            db.commit()
            print(f"Report {report_id} READY: {report.file_path}")
        except Exception as e:
            try:
                report.status = ReportStatus.FAILED
                report.error_message = str(e)[:1000]
                db.add(report)
                db.commit()
            except:
                try: db.rollback()
                except: pass
            print(f"Report {report_id} failed: {e}")
            import traceback; traceback.print_exc()

@router.get("/status/{report_id}")
def report_status(report_id: int, db: Session = Depends(get_db)):
    report = db.exec(select(Report).where(Report.id == report_id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report_id": report.id, "status": str(report.status), "title": report.title, "file_path": report.file_path, "error": report.error_message, "file_size_kb": report.file_size_kb}

@router.get("/download/{report_id}")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = db.exec(select(Report).where(Report.id == report_id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # FIX: if file exists, serve it even if status is still GENERATING - don't block user
    if report.file_path and os.path.exists(report.file_path):
        if report.status != ReportStatus.READY:
            report.status = ReportStatus.READY
            try: db.commit()
            except: pass
    else:
        if report.status != ReportStatus.READY:
            # Give real reason - FAILED shows error, GENERATING shows wait
            if report.status == ReportStatus.FAILED:
                raise HTTPException(status_code=400, detail=f"Report FAILED: {report.error_message or 'Generator error'}. Regenerate.")
            raise HTTPException(status_code=400, detail=f"Report not ready yet. Status: {report.status}. Try /reports/status/{report_id}")
        raise HTTPException(status_code=404, detail=f"File not found at {report.file_path}. Regenerate.")
    if report.expires_at and report.expires_at < datetime.now(UTC):
        report.status = ReportStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=410, detail="Report expired")
    report.download_count += 1
    db.commit()
    media_type = "application/pdf" if report.format == ReportFormat.PDF else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(report.file_path, filename=os.path.basename(report.file_path), media_type=media_type)

@router.get("/list")
def list_reports(db: Session = Depends(get_db)):
    reports = list(db.exec(select(Report).order_by(desc(Report.created_at)).limit(50)))
    return {"reports": [{"id": r.id, "title": r.title, "type": str(r.report_type), "format": str(r.format), "status": str(r.status), "created_at": r.created_at, "downloads": r.download_count, "location": r.town or r.ward or r.sub_county or r.county or r.country, "is_branded": r.is_branded, "file_path": r.file_path, "file_size_kb": r.file_size_kb, "error": r.error_message} for r in reports]}

@router.get("/templates")
def get_templates():
    return {"templates": [
        {"type": "MARKET_FEASIBILITY", "name": "Market Feasibility Report - 12 Engines", "premium": False},
        {"type": "CONSUMER_ANALYSIS", "name": "Consumer Analysis", "premium": False},
        {"type": "INVESTOR_PITCH", "name": "Investor Pitch Deck", "premium": True},
        {"type": "KRA_TAX", "name": "KRA Tax Report", "premium": True},
        {"type": "BUSINESS_PLAN", "name": "Bank Loan Pack", "premium": True},
    ]}
