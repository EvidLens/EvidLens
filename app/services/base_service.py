# app/services/base_service.py
import httpx
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
headers_groq = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}

class BaseService:
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=60.0)

    async def call_groq(self, prompt: str, system: str = "You are EvidLens AI. Be factual, brief, Kenya-focused.") -> str:
        """Central Groq call for all 21 products. Returns string or error message."""
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1024
        }
        try:
            r = await self.client.post(GROQ_URL, json=payload, headers=headers_groq)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            return f"AI unavailable: {e.response.status_code}"
        except Exception:
            return "AI summary unavailable"

    async def call_api(self, url: str, headers: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Generic API caller. Returns data or {'status': 'no_data'} on fail"""
        try:
            r = await self.client.get(url, headers=headers, params=params)
            r.raise_for_status()
            return r.json()
        except:
            return {"status": "no_data"}

    async def close(self):
        await self.client.aclose()
