from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import httpx, os

router = APIRouter()
GROQ_KEY = os.getenv("GROQ_API_KEY")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = []
    context: Optional[dict] = {}

SYSTEM_PROMPT = "You are Lens, the AI assistant for EvidLens - a Decision Intelligence platform for Kenya. Be helpful, brief, and Kenya-specific. Use KES, counties, and local examples. If asked about markets, competitors, or pricing, reference data from the platform. Never make up numbers. If you don't know, say 'I can run an analysis for you'. Keep answers under 4 sentences unless user asks for a report."

@router.post("/chat")
async def chat(req: ChatRequest):
    if not GROQ_KEY:
        return {"reply": "Please add GROQ_API_KEY to enable Lens AI"}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in req.history[-6:]:
        messages.append({"role": msg.role, "content": msg.content})

    if req.context:
        context_str = f"Current user context: Query={req.context.get('query')}, Sector={req.context.get('sector')}, County={req.context.get('county')}, Market Size={req.context.get('market_size_kes')}"
        messages.append({"role": "system", "content": context_str})

    messages.append({"role": "user", "content": req.message})

    ai_res = await httpx.AsyncClient().post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={
            "model": "llama-3.1-70b-versatile",
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.7
        }
    )
    reply = ai_res.json()["choices"][0]["message"]["content"]
    return {"reply": reply}
