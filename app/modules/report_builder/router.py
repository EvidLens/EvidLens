# DEPLOY_FIX_v4_2026-07-14

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta
import httpx

from .service import generate_market_report_pdf, generate_market_report_excel
from .models import Report, ReportType, ReportFormat, ReportStatus
from app.modules.payments.service import get_subscription
from app.modules.db import get_session as get_db

router = APIRouter()
GROQ_KEY = os.getenv("GROQ_API_KEY")

class GenerateReportRequest(BaseModel):
    query: str
    sector: str
    country: str = "Kenya"
    county: Optional[str] = None
    sub_county: Optional[str] = None
    ward: Optional[str] = None
    town: Optional[str] = None
    report_type: ReportType = ReportType.MARKET_FEASIBILITY
    format: ReportFormat = ReportFormat.PDF

@router.post("/generate")
def generate_report(
    req: GenerateReportRequest,
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate report. Checks subscription limits first."""
    sub = get_subscription(db, user_id)

    if sub.reports_left <= 0 and sub.tier.value == "free":
        raise HTTPException(status_code=402, detail="Report limit reached. Upgrade to SME Starter KSH 500 or SME Pro KSH 2000/mo")

    location_str = req.town or req.ward or req.sub_county or req.county or req.country
    report = Report(
        user_id=user_id,
        title=f"{req.report_type.value} - {req.query} @ {location_str}",
        report_type=req.report_type,
        format=req.format,
        query=req.query,
        sector=req.sector,
        country=req.country,
        county=req.county,
        sub_county=req.sub_county,
        ward=req.ward,
        town=req.town,
        status=ReportStatus.GENERATING,
        is_branded=sub.tier.value!= "free"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(process_report_generation, db, report.id, req)

    if sub.tier.value in ["free", "sme_starter"]:
        sub.reports_left -= 1
        db.commit()

    return {
        "report_id": report.id,
        "status": "generating",
        "message": "Report is being generated. Check /reports/list for download"
    }

async def process_report_generation(db: Session, report_id: int, req: GenerateReportRequest):
    """Background task to generate PDF/Excel"""
    report = db.query(Report).filter(Report.id==report_id).first()
    try:
        prompt = f"Generate 6 sections for investor PDF on '{req.query}' in {req.sector} sector, {req.town or req.ward or req.sub_county or req.county}. Kenya context."
        insight = "Add GROQ_API_KEY for full AI report"
        if GROQ_KEY:
            async with httpx.AsyncClient(timeout=30) as client:
                ai_res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}"},
                    json={"model": "llama-3.1-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
                )
                insight = ai_res.json()["choices"][0]["message"]["content"]

        if req.format == ReportFormat.PDF:
            filepath = generate_market_report_pdf(
                db, req.query, req.sector, req.country, req.county,
                req.sub_county, req.ward, req.town
            )
        else:
            filepath = generate_market_report_excel(
                db, req.sector, req.country, req.county,
                req.sub_county, req.ward, req.town, req.query
            )

        report.file_path = filepath
        report.file_size_kb = os.path.getsize(filepath) // 1024
        report.status = ReportStatus.READY
        report.expires_at = datetime.now() + timedelta(days=30 if report.is_branded else 7)
        db.commit()
    except Exception as e:
        report.status = ReportStatus.FAILED
        report.error_message = str(e)
        db.commit()

@router.get("/download/{report_id}")
def download_report(report_id: int, user_id: int, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id==report_id, Report.user_id==user_id).first()
    if not report: raise HTTPException(status_code=404, detail="Report not found")
    if report.status!= ReportStatus.READY: raise HTTPException(status_code=400, detail="Report not ready yet")
    if report.expires_at and report.expires_at < datetime.now():
        report.status = ReportStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=410, detail="Report expired")

    report.download_count += 1
    db.commit()

    media_type = "application/pdf" if report.format == ReportFormat.PDF else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(report.file_path, filename=f"EvidLens_{report.report_type.value}.{report.format.value}", media_type=media_type)

@router.get("/list")
def list_reports(user_id: int, db: Session = Depends(get_db)):
    reports = db.query(Report).filter(Report.user_id==user_id).order_by(Report.created_at.desc()).limit(50).all()
    return {
        "reports": [
            {
                "id": r.id, "title": r.title, "type": r.report_type, "format": r.format,
                "status": r.status, "created_at": r.created_at, "downloads": r.download_count,
                "location": r.town or r.ward or r.sub_county or r.county or r.country,
                "is_branded": r.is_branded
            } for r in reports
        ]
    }

@router.get("/templates")
def get_templates():
    return {
        "templates": [
            {"type": "MARKET_FEASIBILITY", "name": "Market Feasibility Report", "premium": False},
            {"type": "CONSUMER_ANALYSIS", "name": "Consumer Analysis", "premium": False},
            {"type": "INVESTOR_PITCH", "name": "Investor Pitch Deck", "premium": True},
            {"type": "KRA_TAX", "name": "KRA Tax Report", "premium": True},
            {"type": "BUSINESS_PLAN", "name": "Bank Loan Pack", "premium": True},
        ]
    }
