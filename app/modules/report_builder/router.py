from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from.service import generate_market_report_pdf, generate_market_report_excel
from.models import Report, ReportType, ReportFormat, ReportStatus
from app.modules.payments.service import get_subscription
from app.modules.database import get_db
import os
from datetime import datetime, timedelta

router = APIRouter()

class GenerateReportRequest(BaseModel):
    query: str
    sector: str
    county: str
    report_type: ReportType = ReportType.MARKET_FEASIBILITY
    format: ReportFormat = ReportFormat.PDF

@router.post("/generate")
def generate_report(
    req: GenerateReportRequest, 
    user_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate report. Checks subscription limits first"""
    sub = get_subscription(db, user_id)
    
    # Check limits
    if sub.reports_left <= 0 and sub.tier.value == "free":
        raise HTTPException(status_code=402, detail="Report limit reached. Upgrade to SME Starter KSH 500 or SME Pro KSH 2000/mo")
    
    # Create report record
    report = Report(
        user_id=user_id,
        title=f"{req.report_type.value} - {req.query}",
        report_type=req.report_type,
        format=req.format,
        query=req.query,
        sector=req.sector,
        county=req.county,
        status=ReportStatus.GENERATING,
        is_branded=sub.tier.value != "free"
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Generate in background
    background_tasks.add_task(process_report_generation, db, report.id, req)
    
    # Decrement credits
    if sub.tier.value == "free" or sub.tier.value == "sme_starter":
        sub.reports_left -= 1
        db.commit()
    
    return {
        "report_id": report.id,
        "status": "generating",
        "message": "Report is being generated. Check /reports/{id} for download"
    }

def process_report_generation(db: Session, report_id: int, req: GenerateReportRequest):
    """Background task to generate PDF/Excel"""
    report = db.query(Report).filter(Report.id==report_id).first()
    try:
        if req.format == ReportFormat.PDF:
            filepath = generate_market_report_pdf(db, req.query, req.sector, req.county, report.user_id)
        else:
            filepath = generate_market_report_excel(db, req.query, req.sector, req.county)
        
        report.file_path = filepath
        report.file_size_kb = os.path.getsize(filepath) // 1024
        report.status = ReportStatus.READY
        report.expires_at = datetime.now() + timedelta(days=30 if report.is_branded else 7)
        db.commit()
    except Exception as e:
        report.status = ReportStatus.FAILED
        db.commit()

@router.get("/download/{report_id}")
def download_report(report_id: int, user_id: int, db: Session = Depends(get_db)):
    """Download generated report. Checks ownership + expiry"""
    report = db.query(Report).filter(Report.id==report_id, Report.user_id==user_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != ReportStatus.READY:
        raise HTTPException(status_code=400, detail="Report not ready yet")
    
    if report.expires_at and report.expires_at < datetime.now():
        report.status = ReportStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=410, detail="Report expired")
    
    report.download_count += 1
    db.commit()
    
    return FileResponse(
        report.file_path, 
        filename=f"EvidLens_{report.report_type.value}.{report.format.value}",
        media_type="application/pdf" if report.format == ReportFormat.PDF else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/list")
def list_reports(user_id: int, db: Session = Depends(get_db)):
    """Reports Page: Saved reports. KRA format"""
    reports = db.query(Report).filter(Report.user_id==user_id).order_by(Report.created_at.desc()).limit(50).all()
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
                "is_branded": r.is_branded
            } for r in reports
        ]
    }

@router.get("/templates")
def get_templates():
    """List available templates. Premium ones gated in frontend"""
    return {
        "templates": [
            {"type": ReportType.MARKET_FEASIBILITY, "name": "Market Feasibility Report", "premium": False},
            {"type": ReportType.CONSUMER_ANALYSIS, "name": "Consumer Analysis", "premium": False},
            {"type": ReportType.INVESTOR_PITCH, "name": "Investor Pitch Deck", "premium": True},
            {"type": ReportType.KRA_TAX, "name": "KRA Tax Report", "premium": True},
            {"type": ReportType.BUSINESS_PLAN, "name": "Bank Loan Pack", "premium": True},
        ]
    }
