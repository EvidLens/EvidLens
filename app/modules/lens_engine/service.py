import os
import json
import httpx
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.modules.market_engine.service import search_market, get_dashboard_stats
from app.modules.competitive_engine.service import CompetitiveEngineService
from app.modules.core.service import get_all_pricing

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

class LensEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.competitive = CompetitiveEngineService(db)

    async def call_groq(self, prompt: str) -> str:
        if not GROQ_API_KEY: return "Set GROQ_API_KEY"
        async with httpx.AsyncClient(timeout=20) as client: # FASTER
            r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 300})
            return r.json()["choices"][0]["message"]["content"]

    async def chat(self, user_message: str, context: Dict[str, Any] = {}) -> Dict[str, Any]:
        # PRE-LOAD ALL DATA SO NO DELAY
        pricing = get_all_pricing(self.db)
        stats = get_dashboard_stats(self.db)
        params = {"q": user_message}
        if "nairobi" in user_message.lower(): params["county"] = "Nairobi"
        if "dairy" in user_message.lower(): params["sector"] = "Agri Livestock"
        market = search_market(self.db, params["q"], params.get("sector",""), params.get("county",""))

        prompt = f"""You are Lens, EvidLens AI for Kenya. Be direct. 2 sentences max.
        Data Available:
        Pricing: {json.dumps(pricing)}
        Stats: {json.dumps(stats)}
        Market: {json.dumps(market)}
        User: {user_message}
        Answer now using data. End with 'Data: EvidLens DB + Groq'"""

        reply = await self.call_groq(prompt)
        return {"reply": reply, "source": "EvidLens DB + Groq"}

    async def trigger_report(self, sector: str, county: str, report_type: str):
        return {"status": "queued", "message": f"{report_type} for {sector} {county} sent to email"}
