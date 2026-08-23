from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta, timezone
import httpx

from app.modules.auth.dependencies import get_current_user
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
async def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return templates.TemplateResponse("reports_funding.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user
    })

def get_user_plan(db: Session, user_id: int) -> str:
    try:
        stmt = select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.status == "active")
        sub = db.exec(stmt).first()
        if sub:
            return sub.plan_name
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
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1

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
        is_branded=plan_name!= "Trial"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(process_report_generation, report.id, req, plan_name)

    return {"report_id": report.id, "status": "generating", "plan": plan_name, "message": f"Report {report.id} generating with 12 engines LIVE for {q} @ {location_str}. Poll /reports/list or /reports/download/{report.id}"}

def process_report_generation(report_id: int, req: GenerateReportRequest, plan_name: str = "Pro"):
    """Sync background - generates file path for all 12 modules + Quick Analysis"""
    from app.core.db import engine as bg_engine
    from sqlmodel import Session as BgSession
    with BgSession(bg_engine) as db:
        stmt = select(Report).where(Report.id == report_id)
        report = db.exec(stmt).first()
        if not report:
            return
        try:
            insight = ""
            if GROQ_KEY:
                try:
                    import asyncio
                except:
                    pass

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
            else:
                filepath = generate_market_report_excel(db, req.get_sector(), req.country, req.county, req.sub_county, req.ward, req.town, req.get_query())
                if isinstance(filepath, bytes):
                    os.makedirs("app/static/reports", exist_ok=True)
                    filepath = f"app/static/reports/EvidLens_{req.get_query()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                    with open(filepath, "wb") as f:
                        f.write(b"")

            report.file_path = filepath
            try:
                report.file_size_kb = os.path.getsize(filepath) // 1024
            except:
                report.file_size_kb = 0
            report.status = ReportStatus.READY
            report.expires_at = datetime.now(UTC) + timedelta(days=30 if report.is_branded else 7)
            db.commit()
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            db.commit()
            print(f"Report {report_id} failed: {e}")
            import traceback; traceback.print_exc()

@router.get("/download/{report_id}")
def download_report(report_id: int, db: Session = Depends(get_db)):
    stmt = select(Report).where(Report.id == report_id)
    report = db.exec(stmt).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status!= ReportStatus.READY:
        raise HTTPException(status_code=400, detail=f"Report not ready yet. Status: {report.status}. Try /reports/list")
    if report.expires_at and report.expires_at < datetime.now(UTC):
        report.status = ReportStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=410, detail="Report expired")

    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail=f"File not found at {report.file_path}. Regenerate.")

    report.download_count += 1
    db.commit()

    media_type = "application/pdf" if str(report.format) == "ReportFormat.PDF" or report.format == ReportFormat.PDF else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(report.file_path, filename=os.path.basename(report.file_path), media_type=media_type)

@router.get("/list")
def list_reports(db: Session = Depends(get_db)):
    stmt = select(Report).order_by(desc(Report.created_at)).limit(50)
    reports = db.exec(stmt).all()
    return {
        "reports": [
            {
                "id": r.id,
                "title": r.title,
                "type": r.report_type,
                "format": r.format,
                "status": r.status,
                "created_at": r.created_at,
                "downloads": r.download_count,
                "location": r.town or r.ward or r.sub_county or r.county or r.country,
                "is_branded": r.is_branded,
                "file_path": r.file_path,
                "file_size_kb": r.file_size_kb
            } for r in reports
        ]
    }

@router.get("/templates")
def get_templates():
    return {
        "templates": [
            {"type": "MARKET_FEASIBILITY", "name": "Market Feasibility Report - 12 Engines", "premium": False},
            {"type": "CONSUMER_ANALYSIS", "name": "Consumer Analysis", "premium": False},
            {"type": "INVESTOR_PITCH", "name": "Investor Pitch Deck", "premium": True},
            {"type": "KRA_TAX", "name": "KRA Tax Report", "premium": True},
            {"type": "BUSINESS_PLAN", "name": "Bank Loan Pack", "premium": True},
        ]
    }
