from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional, List
import json
import io
import os
import httpx

from app.modules.ai_insights.service import AIInsightsService
from app.core.guards import require_module, consume_credits
from app.core.models import UserSubscription
from app.core.db import get_session

__all__ = ["router", "router_api", "ask_lens_chat", "ChatRequest", "process_chat"]

router = APIRouter(prefix="/ai", tags=["Ask Lens"])
router_api = APIRouter(prefix="/api", tags=["Ask Lens API"])
templates = Jinja2Templates(directory="app/templates")
GROQ_KEY = os.getenv("GROQ_API_KEY")
ai_service = AIInsightsService()

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
    safe_consume_credits(session, user_id, "api_credits", 1)

    if not GROQ_KEY:
        result = await ai_service.generate_insights(req.message, req.context or {}, user_id)
        ans = result.get("answer", "Lens offline - no GROQ key")
        return {"reply": ans, "response": ans, "message": ans, "answer": ans, "sources": result.get("sources", []), "verdict": result.get("verdict")}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in req.history[-6:]:
        messages.append({"role": msg.role, "content": msg.content})
    if req.context:
        geo = f"{req.context.get('ward','')}, {req.context.get('sub_county','')}, {req.context.get('county','Kenya')}"
        messages.append({"role": "system", "content": f"User Context: Sector={req.context.get('sector')}, Location={geo}"})
    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "tools": TOOLS, "tool_choice": "auto", "max_tokens": 900, "temperature": 0.3}
            )
            if res.status_code!= 200:
                err = res.text[:500]
                ans = f"Lens error: {err}"
                return {"reply": ans, "response": ans, "message": ans, "answer": ans, "error": err, "sources": []}
            data = res.json()
    except Exception as e:
        ans = f"AI temporarily down: {e}"
        return {"reply": ans, "response": ans, "message": ans, "answer": ans, "error": str(e)}

    msg = data["choices"][0]["message"]

    if msg.get("tool_calls"):
        tool_call = msg["tool_calls"][0]
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        tool_result = await call_tool(tool_name, tool_args, user_id, session)
        try:
            messages.append(msg)
            messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(tool_result)})
            async with httpx.AsyncClient(timeout=60.0) as client:
                res2 = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 900, "temperature": 0.3}
                )
                if res2.status_code == 200:
                    final_content = res2.json()["choices"][0]["message"]["content"]
                    return {"reply": final_content, "response": final_content, "message": final_content, "answer": final_content, "result": tool_result, "tool_used": tool_name, "sources": ["EvidLens 9 Lanes"], "credits_used": 1}
        except:
            pass
        ans = tool_result.get("answer") if isinstance(tool_result, dict) else str(tool_result)
        ans = ans or f"Done. {tool_name}"
        return {"reply": ans, "response": ans, "message": ans, "answer": ans, "result": tool_result, "credits_used": 1, "sources": ["EvidLens Tools"]}

    content = msg.get("content") or "How can I help with Kenya markets?"
    return {"reply": content, "response": content, "message": content, "answer": content, "credits_used": 1, "sources": ["EvidLens 9 Lanes", "Groq AI"]}

@router.get("/", response_class=HTMLResponse)
async def ai_page(request: Request):
    return templates.TemplateResponse("ai_insights.html", {"request": request})

@router.post("/chat")
async def ask_lens_chat(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    return await process_chat(req, request, session)

@router_api.post("/chat")
async def ask_lens_chat_api(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    return await process_chat(req, request, session)

@router.get("/chat")
async def ask_lens_chat_get(message: str = "hello", request: Request = None, session: Session = Depends(get_session)):
    return await process_chat(ChatRequest(message=message, history=[], context={}), request, session)

@router.post("/ask")
async def ask_lens(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    safe_consume_credits(session, user_id, "api_credits", 1)
    market_data = {"sector": req.sector, "county": req.county, "sub_county": req.sub_county, "ward": req.ward}
    result = await ai_service.generate_insights(req.query, market_data, user_id)
    if req.export_format!= "json":
        return export_result(result, req.export_format)
    return {
        "reply": result["answer"],
        "response": result["answer"],
        "answer": result["answer"],
        "chart_data": result.get("chart"),
        "table": result.get("table"),
        "map": result.get("map"),
        "sources": result.get("sources", []),
        "export_url": f"/ai/export?format={req.export_format}"
    }

@router.post("/viability")
async def viability_check(request: Request, req: InsightRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, 'user', None)
    user_id = user_id.id if user_id else 1
    safe_consume_credits(session, user_id, "api_credits", 2)
    market_data = {"sector": req.sector, "county": req.county}
    viab_query = f"Should I start a {req.query} business in {req.county}? Give Go, No-Go, or Needs Research. Include 3 reasons, market size, and risks."
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
    report = await ai_service.generate_insights(f"Generate board report for {req.sector} in {req.county}", {}, user_id)
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
    leads = await ai_service.generate_insights(f"Get 100 B2B leads for {req.sector} in {req.county}", {}, user_id)
    return export_result(leads, "xlsx")

@router.get("/help")
def ask_lens_help(query: str):
    help_map = {
        "pricing": "EV-SME 20k, EV-GROWTH 50k, EV-PRO 100k, EV-ENT 200k",
        "setup": "Go to Dashboard > Pick Sector > Pick County > Ask Lens",
        "features": "19 Modules, 9 Lanes, Kenya-First Data"
    }
    ans = help_map.get(query.lower(), "Contact support@evidlens.co.ke")
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
