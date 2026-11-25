from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional, List, Any
import json
import io
import os
import httpx
from app.modules.ai_insights.service import AIInsightsService
from app.modules.lens_engine.service import LensEngineService
from app.core.guards import require_module, consume_credits
from app.core.models import UserSubscription
from app.core.db import get_session
__all__ = ["router", "router_api", "ask_lens_chat", "ChatRequest", "process_chat"]
router = APIRouter(prefix="/ai", tags=["Ask Lens"])
router_api = APIRouter(prefix="/api", tags=["Ask Lens API"])
templates = Jinja2Templates(directory="app/templates")
GROQ_KEY = os.getenv("GROQ_API_KEY")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@evidlens.co.ke")
ai_service = AIInsightsService()
class InsightRequest(BaseModel):
    query: str
    sector: str
    county: Optional[str] = None
    sub_county: Optional[str] = None
    ward: Optional[str] = None
    export_format: Optional[str] = "json"
    budget_kes: Optional[int] = None
class AlertRequest(BaseModel):
    alert_type: str
    keywords: List[str]
    channel: str
class Message(BaseModel):
    role: str
    content: str
class ChatRequest(BaseModel):
    message: Optional[str] = ""
    history: Optional[List[Message]] = []
    context: Optional[dict] = {}
    product: Optional[str] = None
    query: Optional[str] = None
    q: Optional[str] = None
    sector: Optional[str] = None
    county: Optional[str] = None
    budget: Optional[Any] = None
    budget_kes: Optional[Any] = None
    model_config = {"extra": "allow"}
SYSTEM_PROMPT = """You are Ask Lens, the AI Agent for EvidLens Kenya Decision Intelligence.
You have access to 9 Lanes of Kenya data: MarketPrice, BusinessDirectory, DemandSignal, CountyStats, Sectors, Opportunities.
Personality: Real human, smart, warm, slightly playful, Kenyan. Talk like ChatGPT, not a form. Keep replies 2-5 sentences unless user asks for a full report. Always give 1 actionable next step. Currency KES, counties only.
Rules:
If user says hi/hello/hey/niaje/sasa: greet warmly in 1 sentence, ask what business they are exploring. Do NOT give 8 sections.
If user says vague like 'i need something' / 'help' / 'i need help': ask ONE question only: What product or business are you thinking about? Do NOT ask for product + county + budget + timeline all at once.
If user gives a real product/business but no county or budget: DO NOT block. Assume nationwide, KES 500000, 12 months, say you assumed that, and give the answer. Ask for county/budget at the end in 1 line if needed.
If user asks for full report / analysis / viability / business case / detailed: give DETAILED analysis in 8 sections: 1. EXECUTIVE SUMMARY with Go/No-Go Score /10 2. MARKET SIZE & DEMAND - Total Market Size KES, Demand Score /10, Volume, Growth % 3. PRICING INTELLIGENCE - Live KES table: Product | Avg Price | Market | County 4. COMPETITOR LANDSCAPE - 5 Real Businesses with Rating, Reviews, County 5. COUNTY DEEP DIVE - Market Size, Best Subcounty, Best Ward 6. FINANCIAL VIABILITY - For Budget KES: Startup breakdown, Break-even months, Monthly Profit, ROI% 7. RISKS & MITIGATION - 3 Risks 8. ACTION PLAN - 30 Days
Use KES, counties, sub-counties, wards. Cite KNBS, CBK, KRA, MarketPrice, BusinessDirectory. Never brief when full report asked. Minimum 400 words for full report. If no DB data, ESTIMATE with Kenya benchmarks but label as Estimated.
"""
TOOLS = [
    {"type": "function", "function": {"name": "data_qa", "description": "Answer questions using 9 Lanes data DETAILED", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "sector": {"type": "string"}, "county": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "generate_report", "description": "Build detailed board deck, PDF, PPT", "parameters": {"type": "object", "properties": {"type": {"type": "string"}, "sector": {"type": "string"}, "county": {"type": "string"}}, "required": ["type"]}}},
    {"type": "function", "function": {"name": "create_alert", "description": "Set alert", "parameters": {"type": "object", "properties": {"alert_type": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}, "channel": {"type": "string"}}, "required": ["alert_type", "keywords"]}}},
    {"type": "function", "function": {"name": "export_data", "description": "Export to Excel, PDF DETAILED", "parameters": {"type": "object", "properties": {"format": {"type": "string"}}, "required": ["format"]}}},
    {"type": "function", "function": {"name": "viability_check", "description": "Detailed Go, No-Go, Needs Research with financials", "parameters": {"type": "object", "properties": {"business": {"type": "string"}, "county": {"type": "string"}, "budget": {"type": "string"}}, "required": ["business", "county"]}}}
]
async def call_tool(name: str, args: dict, user_id: int, session: Session):
    if name == "data_qa":
        return await ai_service.generate_insights(args["query"], args, user_id)
    if name == "viability_check":
        return await ai_service.generate_insights(f"Should I start {args['business']} in {args['county']}? Budget {args.get('budget','')}. Give DETAILED Go/No-Go with market size, financials, 3 risks, 30-day plan.", args, user_id)
    if name == "generate_report":
        return {"status": "Report queued", "type": args["type"], "download_url": f"/api/reports/download?module={args.get('sector','all')}"}
    if name == "create_alert":
        return {"status": "Alert created", "channel": args["channel"], "keywords": args["keywords"]}
    if name == "export_data":
        return {"status": "Export ready", "format": args["format"], "download_url": "/api/reports/download"}
    return {"error": "Tool not found"}
def safe_consume_credits(session, user_id, credit_type="api_credits", amount=1):
    try:
        sub = session.get(UserSubscription, user_id)
        if sub and hasattr(sub, credit_type) and getattr(sub, credit_type) >= amount:
            setattr(sub, credit_type, getattr(sub, credit_type) - amount)
            session.commit()
    except:
        pass
async def process_chat(req: ChatRequest, request: Request, session: Session):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    user_email = getattr(getattr(request.state, 'user', None), 'email', None) or "anon@evidlens.co.ke"
    safe_consume_credits(session, user_id, "api_credits", 1)
    history = [{"role": m.role, "content": m.content} for m in (req.history or [])]
    if req.context:
        ctx_parts = []
        if req.context.get("county"):
            ctx_parts.append(f"County={req.context.get('county')}")
        if req.context.get("sub_county"):
            ctx_parts.append(f"SubCounty={req.context.get('sub_county')}")
        if req.context.get("ward"):
            ctx_parts.append(f"Ward={req.context.get('ward')}")
        if req.context.get("sector"):
            ctx_parts.append(f"Sector={req.context.get('sector')}")
        if req.context.get("budget_kes"):
            ctx_parts.append(f"Budget={req.context.get('budget_kes')} KES")
        if ctx_parts:
            full_message = f"{req.message}\n\nUser Context: {', '.join(ctx_parts)}"
        else:
            full_message = req.message
    else:
        full_message = req.message
    low = req.message.lower().strip()
    wants_report = any(k in low for k in ["full report", "detailed", "analysis", "viability", "business case", "business plan", "should i start", "market size", "30-day", "30 day", "action plan", "financial"])
    if wants_report:
        market_data = dict(req.context or {})
        market_data["sector"] = market_data.get("sector") or "General"
        market_data["county"] = market_data.get("county") or "Kenya"
        result = await ai_service.generate_insights(req.message, market_data, user_id)
        ans = result.get("answer", "")
        return {"reply": ans, "response": ans, "message": ans, "answer": ans, "sources": result.get("sources", []), "verdict": result.get("verdict"), "credits_used": 1}
    lens = LensEngineService(session)
    result = await lens.chat(full_message, user_email, history)
    ans = result.get("reply", "") or "How can I help with Kenya markets?"
    return {"reply": ans, "response": ans, "message": ans, "answer": ans, "sources": [result.get("source", "EvidLens DB + Groq")], "verdict": None, "credits_used": 1, "model": lens.groq_model}
@router.get("/", response_class=HTMLResponse)
async def ai_page(request: Request):
    return templates.TemplateResponse("ai_insights.html", {"request": request})
@router.post("/chat")
async def ask_lens_chat(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    return await process_chat(req, request, session)
@router_api.post("/chat")
async def ask_lens_chat_api(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    return await process_chat(req, request, session)
@router_api.post("/analyze")
async def analyze_api(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    if not req.message:
        msg = req.product or req.query or req.q or ""
        if req.sector:
            msg += f" in {req.sector}"
        if req.county:
            msg += f" in {req.county}"
        if not msg.strip():
            msg = "Give me a detailed market analysis"
        req.message = msg
        ctx = dict(req.context or {})
        if req.sector:
            ctx["sector"] = req.sector
        if req.county:
            ctx["county"] = req.county
        if req.budget_kes or req.budget:
            ctx["budget_kes"] = req.budget_kes or req.budget
        req.context = ctx
    return await process_chat(req, request, session)
@router.get("/chat")
async def ask_lens_chat_get(message: str = "hello", request: Request = None, session: Session = Depends(get_session)):
    return await process_chat(ChatRequest(message=message, history=[], context={}), request, session)
@router.post("/ask")
async def ask_lens(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    safe_consume_credits(session, user_id, "api_credits", 1)
    market_data = {"sector": req.sector, "county": req.county, "sub_county": req.sub_county, "ward": req.ward, "budget_kes": req.budget_kes}
    result = await ai_service.generate_insights(req.query, market_data, user_id)
    if req.export_format != "json":
        return export_result(result, req.export_format)
    return {"reply": result["answer"], "response": result["answer"], "answer": result["answer"], "chart_data": result.get("chart"), "table": result.get("table"), "map": result.get("map"), "sources": result.get("sources", []), "verdict": result.get("verdict"), "export_url": f"/ai/export?format={req.export_format}"}
@router.post("/viability")
async def viability_check(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    safe_consume_credits(session, user_id, "api_credits", 2)
    market_data = {"sector": req.sector, "county": req.county, "budget_kes": req.budget_kes}
    viab_query = f"Should I start a {req.query} business in {req.county}? Budget KES {req.budget_kes}. Give DETAILED Go, No-Go, or Needs Research. Include 8 sections: executive summary, market size KES, pricing table, 5 competitors, county deep dive, financial viability with break-even, monthly profit, ROI%, 3 risks, 30-day action plan."
    result = await ai_service.generate_insights(viab_query, market_data, user_id)
    ans = result["answer"]
    return {"reply": ans, "response": ans, "answer": ans, "analysis": ans, "verdict": result.get("verdict"), "sources": result.get("sources")}
@router.post("/alerts/create")
def create_alert(request: Request, req: AlertRequest):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    return {"reply": f"Alert for {req.alert_type} created", "response": f"Alert for {req.alert_type} created", "status": "Alert created", "type": req.alert_type, "channel": req.channel}
@router.post("/reports/generate")
async def generate_report(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    safe_consume_credits(session, user_id, "api_credits", 5)
    report = await ai_service.generate_insights(f"Generate DETAILED board report for {req.sector} in {req.county} with 8 sections", {}, user_id)
    return export_result(report, "pptx")
@router.post("/leads/export")
async def export_leads(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    try:
        sub = session.get(UserSubscription, user_id)
        if sub and sub.lead_credits < 100:
            raise HTTPException(status_code=402, detail="Buy lead credits")
        safe_consume_credits(session, user_id, "lead_credits", 100)
    except HTTPException:
        raise
    except:
        pass
    leads = await ai_service.generate_insights(f"Get 100 B2B leads for {req.sector} in {req.county} with contacts", {}, user_id)
    return export_result(leads, "xlsx")
@router.get("/help")
def ask_lens_help(query: str):
        help_map = {"pricing": "Starter KES 500/mo (5,000/yr), Pro KES 1,500/mo (15,000/yr), Enterprise KES 5,000/mo (50,000/yr). Pay with M-Pesa. Yearly = 2 months free.", "setup": "Go to Dashboard > Pick Sector > Pick County > Ask Lens", "features": "19 Modules, 9 Lanes, Kenya-First Data"}
    ans = help_map.get(query.lower(), f"Contact {SUPPORT_EMAIL}")
    return {"reply": ans, "response": ans, "answer": ans}
def export_result(data, format):
    if format == "xlsx":
        output = io.BytesIO()
        return StreamingResponse(output, media_type="application/vnd.ms-excel")
    if format == "pdf":
        return StreamingResponse(io.BytesIO(b"PDF"), media_type="application/pdf")
    if format == "pptx":
        return StreamingResponse(io.BytesIO(b"PPTX"), media_type="application/vnd.openxmlformats")
    return data
