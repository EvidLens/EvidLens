from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx, os, json
from sqlmodel import Session
from app.modules.data_layer.models import *
from app.modules.data_layer.db import get_session

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

def generate_insights_local(user_message: str, context: dict):
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": "You are EvidLens AI. Give market insights for Kenyan farmers and SMEs. Be concise. Use KES and Counties."},{"role": "user", "content": user_message}],
        max_tokens=800, temperature=0.3
    )
    return completion.choices[0].message.content

async def call_tool(name: str, args: dict, user_id: int, session: Session):
    if name == "data_qa":
        return {"answer": generate_insights_local(args["query"], args)}
    if name == "viability_check":
        return {"answer": generate_insights_local(f"Should I start {args['business']} in {args['county']}? Give Go/No-Go with 3 reasons.", args)}
    if name == "generate_report":
        return {"status": "Report queued", "type": args["type"]}
    if name == "create_alert":
        return {"status": "Alert created", "channel": args["channel"]}
    if name == "export_data":
        return {"status": "Export ready", "format": args["format"]}
    return {"error": "Tool not found"}

@router.post("/chat")
async def ask_lens_chat(request: Request, req: ChatRequest, session: Session = Depends(get_session)):
    user_id = getattr(request.state, "user", None)
    user_id = user_id.id if user_id else 1

    if not GROQ_KEY:
        return {"reply": "Lens is offline. Please add GROQ_API_KEY"}

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
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "tools": TOOLS, "tool_choice": "auto", "max_tokens": 800, "temperature": 0.3}
            )
            res.raise_for_status()
            data = res.json()
    except Exception as e:
        return {"reply": f"AI Error: {str(e)}", "credits_used": 0}

    msg = data["choices"][0]["message"]

    if msg.get("tool_calls"):
        tool_call = msg["tool_calls"][0]
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        tool_result = await call_tool(tool_name, tool_args, user_id, session)
        return {"reply": tool_result.get("answer", f"Done. I ran: {tool_name}"), "result": tool_result}

    return {"reply": msg["content"], "sources": ["EvidLens 9 Lanes"]}
