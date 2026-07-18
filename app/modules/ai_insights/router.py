from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional, List
from .service import generate_insights
from app.modules.core.guards import require_module, consume_credits
from app.modules.core.models import UserSubscription
from app.modules.database import get_session
import json
import io

router = APIRouter(prefix="/ai", tags=["Ask Lens"])

class InsightRequest(BaseModel):
    query: str
    sector: str
    county: Optional[str] = None
    sub_county: Optional[str] = None
    ward: Optional[str] = None
    export_format: Optional[str] = "json"

class AlertRequest(BaseModel):
    alert_type: str
    keywords: List[str]
    channel: str

@router.post("/ask")
@require_module(module_number=3)
def ask_lens(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id

    market_data = {
        "sector": req.sector,
        "county": req.county,
        "sub_county": req.sub_county,
        "ward": req.ward
    }

    result = generate_insights(req.query, market_data, user_id)

    if req.export_format!= "json":
        consume_credits(session, user_id, "api_credits", 1)
        return export_result(result, req.export_format)

    return {
        "answer": result["answer"],
        "chart_data": result.get("chart"),
        "table": result.get("table"),
        "map": result.get("map"),
        "sources": result.get("sources", []),
        "export_url": f"/ai/export?format={req.export_format}"
    }

@router.post("/viability")
@require_module(module_number=3)
def viability_check(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    market_data = {"sector": req.sector, "county": req.county}
    viab_query = f"Should I start a {req.query} business in {req.county}? Give Go, No-Go, or Needs Research. Include 3 reasons, market size, and risks."
    result = generate_insights(viab_query, market_data, user_id)
    consume_credits(session, user_id, "api_credits", 2)
    return {"analysis": result["answer"], "verdict": result.get("verdict"), "sources": result.get("sources")}

@router.post("/alerts/create")
@require_module(module_number=10)
def create_alert(request: Request, req: AlertRequest):
    user_id = request.state.user.id
    return {"status": "Alert created", "type": req.alert_type, "channel": req.channel}

@router.post("/reports/generate")
@require_module(module_number=10)
def generate_report(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    report = generate_insights(f"Generate board report for {req.sector} in {req.county}", {}, user_id)
    consume_credits(session, user_id, "api_credits", 5)
    return export_result(report, "pptx")

@router.post("/leads/export")
@require_module(module_number=17)
def export_leads(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    sub = session.get(UserSubscription, user_id)
    if sub.lead_credits < 100:
        raise HTTPException(status_code=402, detail="Buy lead credits")
    consume_credits(session, user_id, "lead_credits", 100)
    leads = generate_insights(f"Get 100 B2B leads for {req.sector} in {req.county}", {}, user_id)
    return export_result(leads, "xlsx")

@router.get("/help")
def ask_lens_help(query: str):
    help_map = {
        "pricing": "EV-SME 20k, EV-GROWTH 50k, EV-PRO 100k, EV-ENT 200k",
        "setup": "Go to Dashboard > Pick Sector > Pick County > Ask Lens",
        "features": "19 Modules, 9 Lanes, Kenya-First Data"
    }
    return {"answer": help_map.get(query.lower(), "Contact support@evidlens.co.ke")}

def export_result(data, format):
    if format == "xlsx":
        df = data.get("table", [])
        output = io.BytesIO()
        return StreamingResponse(output, media_type="application/vnd.ms-excel")
    if format == "pdf":
        return StreamingResponse(io.BytesIO(b"PDF"), media_type="application/pdf")
    if format == "pptx":
        return StreamingResponse(io.BytesIO(b"PPTX"), media_type="application/vnd.openxmlformats")
    return data
