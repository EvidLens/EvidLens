import os, json, httpx, requests, pandas as pd
from sqlalchemy.orm import Session
from sqlmodel import select, func, desc, asc
from datetime import datetime
from typing import Dict, Any
from app.modules.database import MarketMetric, KenyaLensBusiness, Session as DBSession, engine, send_support_ticket # add this import

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are EvidLens AI. You give market insights for Kenyan farmers and SMEs.
Rules:
1. Be concise. Max 4 sentences. Data-driven. Use KES and Counties.
2. If user asks "how do I...", guide them step by step through the app features.
3. If user says "problem", "bug", "not working", "help", "support" -> You MUST call raise_ticket function. End with: "Should I raise a ticket for you?"
4. If no data, say "No data yet for X county".
5. Always give 1 actionable next step.
"""

class LensEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def call_groq(self, user_message: str, context: str, user_email: str) -> str:
        if not GROQ_API_KEY:
            return "Error: Set GROQ_API_KEY in.env"

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT + context},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 350,
                    "tools": [{
                        "type": "function",
                        "function": {
                            "name": "raise_ticket",
                            "description": "Raise a support ticket to EvidLens team at support@evidlens.co.ke",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "subject": {"type": "string"},
                                    "description": {"type": "string"}
                                },
                                "required": ["subject", "description"]
                            }
                        }
                    }],
                    "tool_choice": "auto"
                })
            data = r.json()
            message = data["choices"][0]["message"]

        # 2. HANDLE FUNCTION CALL
        if "tool_calls" in message:
            for tool_call in message["tool_calls"]:
                if tool_call["function"]["name"] == "raise_ticket":
                    args = json.loads(tool_call["function"]["arguments"])
                    sent = send_support_ticket(args['subject'], args['description'], user_email)
                    if sent:
                        return "Ticket raised successfully. Our team at support@evidlens.co.ke will reply within 24hrs."
                    else:
                        return "Could not send ticket. Please email us directly at support@evidlens.co.ke"
        return message.get("content", "No response")

    async def chat(self, user_message: str, user_email: str) -> Dict[str, Any]:
        stats = dashboard_api(self.db) # reuse your function
        market = [m.dict() for m in self.db.exec(select(MarketMetric).limit(5)).all()]
        context = f"\nData: Stats={json.dumps(stats['stats'])} Market={json.dumps(market)}"

        reply = await self.call_groq(user_message, context, user_email)
        return {"reply": reply, "source": "EvidLens DB + Groq"}

    async def generate_sector_insights(self, sector: str, county: str = None) -> Dict[str, Any]:
        q = select(MarketMetric).where(MarketMetric.sector == sector)
        if county: q = q.where(MarketMetric.county == county)
        market = [m.dict() for m in self.db.exec(q.limit(10)).all()]
        if not market:
            return {"reply": f"No data yet for {county or sector} county", "source": "EvidLens DB"}

        context = f"\nData: Market={json.dumps(market)}"
        reply = await self.call_groq(f"Give insights for {sector} in {county}", context, "")
        return {"insights": reply, "source": "EvidLens DB + Groq"}
