from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
import httpx, os, json
from app.modules.database import get_session
from app.modules.core.guards import require_module, consume_credits
from sqlmodel import Session
from app.modules.ai_insights.service import generate_insights

router = APIRouter(prefix="/lens", tags=["Ask Lens"])
GROQ_KEY = os.getenv("GROQ_API_KEY")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []
    context: Optional[dict] = {}

SYSTEM_PROMPT = """You are Ask Lens, the AI Agent for EvidLens Kenya Decision Intelligence.
You have access to 9 Lanes of Kenya data. Be brief, use KES, counties, sub-counties.
Rules:
1. Cite sources like KNBS, CBK, KRA
2. Max 4 sentences unless user asks for "report"
3. If asked for report/export/alert/viability, call the correct tool
Available tools: data_qa, generate_report, create_alert, export_data, viability_check
"""

TOOLS = [
    {"type": "function", "function": {"name": "data_qa", "description": "Answer questions using 9 Lanes data", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "sector": {"type": "string"}, "county": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "generate_report", "description": "Build board deck, PDF, PPT, proposal", "parameters": {"type": "object", "properties": {"type": {"type": "string"}, "sector": {"type": "string"}, "county": {"type": "string"}}, "required": ["type"]}}},
    {"type": "function", "function": {"name": "create_alert", "description": "Set alert for competitor, price, tender. Sends via WhatsApp, Email, Slack", "parameters": {"type": "object", "properties": {"alert_type": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}, "channel": {"type": "string"}}, "required": ["alert_type", "keywords"]}}},
    {"type": "function", "function": {"name": "export_data", "description": "Export answer to Excel, PDF, PPT", "parameters": {"type": "object", "properties": {"format": {"type": "string"}, "data": {"type": "object"}}, "required": ["format"]}}},
    {"type": "function", "function": {"name": "viability_check", "description": "Go, No-Go, Needs Research for a business", "parameters": {"type": "object", "properties": {"business": {"type": "string"}, "county": {"type": "string"}}, "required": ["business", "county"]}}}
]

async def call_tool(name: str, args: dict, user_id: int, session: Session):
    if name == "data_qa":
        return generate_insights(args["query"], args)
    if name == "viability_check":
        return generate_insights(f"Should I start {args['business']} in {args['county']}? Give Go/No-Go.", args)
    if name == "generate_report":
        return {"status": "Report queued", "type": args["type"], "eta": "2 mins"}
    if name == "create_alert":
        return {"status": "Alert created", "channel": args["channel"], "keywords": args["keywords"]}
    if name == "export_data":
        return {"status": "Export ready", "format": args["format"], "download_url": "/exports/temp.xlsx"}
    return {"error": "Tool not found"}

@router.post("/chat")
@require_module(module_number=3)
async def ask_lens_chat(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    if not GROQ_KEY:
        return {"reply": "Lens is offline. Please add GROQ_API_KEY"}

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

    data = res.json()
    msg = data["choices"][0]["message"]

    if msg.get("tool_calls"):
        tool_call = msg["tool_calls"][0]
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        tool_result = await call_tool(tool_name, tool_args, user_id, session)
        return {"reply": f"Done. I ran: {tool_name}", "result": tool_result, "credits_used": 1}

    return {"reply": msg["content"], "credits_used": 1, "sources": ["EvidLens 9 Lanes"]}
