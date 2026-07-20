from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional, List
import json
import io
import os
import httpx

from app.modules.ai_insights.service import AIInsightsService
from app.modules.core.guards import require_module, consume_credits
from app.modules.core.models import UserSubscription
from app.modules.database import get_session

__all__ = ["router", "ask_lens_chat", "ChatRequest"]

router = APIRouter(prefix="/ai", tags=["Ask Lens"])
GROQ_KEY = os.getenv("GROQ_API_KEY")
ai_service = AIInsightsService()

# EXISTING MODELS
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

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []
    context: Optional[dict] = {}

SYSTEM_PROMPT = """You are Ask Lens, the AI Agent for EvidLens Kenya Decision Intelligence.
You have access to 9 Lanes of Kenya data. Be brief, use KES, counties, sub-counties.
Cite KNBS, CBK, KRA. If no DB data, say "No data yet. Ingest to unlock."
Max 4 sentences unless user asks for "report".
Available tools: data_qa, generate_report, create_alert, export_data, viability_check
"""

TOOLS = [
    {"type": "function", "function": {"name": "data_qa", "description": "Answer questions using 9 Lanes data", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "sector": {"type": "string"}, "county": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "generate_report", "description": "Build board deck, PDF, PPT", "parameters": {"type": "object", "properties": {"type": {"type": "string"}, "sector": {"type": "string"}, "county": {"type": "string"}}, "required": ["type"]}}},
    {"type": "function", "function": {"name": "create_alert", "description": "Set alert", "parameters": {"type": "object", "properties": {"alert_type": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}, "channel": {"type": "string"}}, "required": ["alert_type", "keywords"]}}},
    {"type": "function", "function": {"name": "export_data", "description": "Export to Excel, PDF", "parameters": {"type": "object", "properties": {"format": {"type": "string"}}, "required": ["format"]}}},
    {"type": "function", "function": {"name": "viability_check", "description": "Go, No-Go, Needs Research", "parameters": {"type": "object", "properties": {"business": {"type": "string"}, "county": {"type": "string"}}, "required": ["business", "county"]}}}
]

async def call_tool(name: str, args: dict, user_id: int, session: Session):
    if name == "data_qa":
        return await ai_service.generate_insights(args["query"], args, user_id)
    if name == "viability_check":
        return await ai_service.generate_insights(f"Should I start {args['business']} in {args['county']}? Give Go/No-Go.", args, user_id)
    if name == "generate_report":
        return {"status": "Report queued", "type": args["type"], "download_url": f"/api/reports/download?module={args.get('sector','all')}"}
    if name == "create_alert":
        return {"status": "Alert created", "channel": args["channel"], "keywords": args["keywords"]}
    if name == "export_data":
        return {"status": "Export ready", "format": args["format"], "download_url": "/api/reports/download"}
    return {"error": "Tool not found"}

@router.post("/chat")
@require_module(module_number=3)
async def ask_lens_chat(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1

    if not GROQ_KEY:
        raise HTTPException(500, "Lens is offline. Please add GROQ_API_KEY")

    consume_credits(session, user_id, "api_credits", 1)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in req.history[-6:]:
        messages.append({"role": msg.role, "content": msg.content})
    if req.context:
        geo = f"{req.context.get('ward','')}, {req.context.get('sub_county','')}, {req.context.get('county','Kenya')}"
        messages.append({"role": "system", "content": f"User Context: Sector={req.context.get('sector')}, Location={geo}"})
    messages.append({"role": "user", "content": req.message})

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.1-70b-versatile", "messages": messages, "tools": TOOLS, "tool_choice": "auto", "max_tokens": 800, "temperature": 0.3}
        )

    if res.status_code!= 200:
        return {"reply": "Lens error. Try again.", "error": res.text}

    data = res.json()
    msg = data["choices"][0]["message"]

    if msg.get("tool_calls"):
        tool_call = msg["tool_calls"][0]
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        tool_result = await call_tool(tool_name, tool_args, user_id, session)
        return {"reply": f"Done. {tool_name}", "result": tool_result, "credits_used": 1}

    return {"reply": msg["content"], "credits_used": 1, "sources": ["EvidLens 9 Lanes", "Groq AI"]}

@router.post("/ask")
@require_module(module_number=3)
async def ask_lens(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    market_data = {"sector": req.sector, "county": req.county, "sub_county": req.sub_county, "ward": req.ward}
    result = await ai_service.generate_insights(req.query, market_data, user_id)
    if req.export_format!= "json":
        consume_credits(session, user_id, "api_credits", 1)
        return export_result(result, req.export_format)
    return {
        "answer": result["answer"], "chart_data": result.get("chart"), "table": result.get("table"),
        "map": result.get("map"), "sources": result.get("sources", []), "export_url": f"/ai/export?format={req.export_format}"
    }

@router.post("/viability")
@require_module(module_number=3)
async def viability_check(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    market_data = {"sector": req.sector, "county": req.county}
    viab_query = f"Should I start a {req.query} business in {req.county}? Give Go, No-Go, or Needs Research. Include 3 reasons, market size, and risks."
    result = await ai_service.generate_insights(viab_query, market_data, user_id)
    consume_credits(session, user_id, "api_credits", 2)
    return {"analysis": result["answer"], "verdict": result.get("verdict"), "sources": result.get("sources")}

@router.post("/alerts/create")
@require_module(module_number=10)
def create_alert(request: Request, req: AlertRequest):
    user_id = request.state.user.id
    return {"status": "Alert created", "type": req.alert_type, "channel": req.channel}

@router.post("/reports/generate")
@require_module(module_number=10)
async def generate_report(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    report = await ai_service.generate_insights(f"Generate board report for {req.sector} in {req.county}", {}, user_id)
    consume_credits(session, user_id, "api_credits", 5)
    return export_result(report, "pptx")

@router.post("/leads/export")
@require_module(module_number=17)
async def export_leads(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    sub = session.get(UserSubscription, user_id)
    if sub.lead_credits < 100:
        raise HTTPException(status_code=402, detail="Buy lead credits")
    consume_credits(session, user_id, "lead_credits", 100)
    leads = await ai_service.generate_insights(f"Get 100 B2B leads for {req.sector} in {req.county}", {}, user_id)
    return export_result(leads, "xlsx")

@router.get("/help")
def ask_lens_help(query: str):
    help_map = {"pricing": "EV-SME 20k, EV-GROWTH 50k, EV-PRO 100k, EV-ENT 200k", "setup": "Go to Dashboard > Pick Sector > Pick County > Ask Lens", "features": "19 Modules, 9 Lanes, Kenya-First Data"}
    return {"answer": help_map.get(query.lower(), "Contact support@evidlens.co.ke")}

def export_result(data, format):
    if format == "xlsx":
        output = io.BytesIO()
        return StreamingResponse(output, media_type="application/vnd.ms-excel")
    if format == "pdf":
        return StreamingResponse(io.BytesIO(b"PDF"), media_type="application/pdf")
    if format == "pptx":
        return StreamingResponse(io.BytesIO(b"PPTX"), media_type="application/vnd.openxmlformats")
    return data
