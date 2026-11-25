import httpx
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger("evidlens.base_service")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_SYSTEM = "You are EvidLens AI. Be factual, brief, Kenya-focused."

class BaseService:
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))

    def _groq_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}

    async def call_groq(self, prompt: str, system: str = DEFAULT_SYSTEM, max_tokens: int = 1024, temperature: float = 0.2) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return ""
        if not getattr(settings, "GROQ_API_KEY", ""):
            logger.error("GROQ_API_KEY missing")
            return "AI unavailable: not configured"
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        last_error = "AI summary unavailable"
        for attempt in range(3):
            try:
                r = await self.client.post(GROQ_URL, json=payload, headers=self._groq_headers())
                if r.status_code == 429:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    last_error = "AI unavailable: 429"
                    continue
                r.raise_for_status()
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                if content:
                    return content.strip()
                return "AI summary unavailable"
            except httpx.HTTPStatusError as e:
                last_error = f"AI unavailable: {e.response.status_code}"
                logger.warning(f"Groq HTTP {e.response.status_code} attempt {attempt + 1}")
                if e.response.status_code in (400, 401, 403):
                    break
                await asyncio.sleep(0.5 * (attempt + 1))
            except httpx.TimeoutException:
                last_error = "AI unavailable: timeout"
                logger.warning(f"Groq timeout attempt {attempt + 1}")
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                logger.exception(f"Groq error: {e}")
                last_error = "AI summary unavailable"
                break
        return last_error

    async def call_api(self, url: str, headers: Optional[Dict] = None, params: Optional[Dict] = None, timeout: float = 15.0) -> Dict[str, Any]:
        if not url or not url.startswith("https://"):
            return {"status": "no_data"}
        try:
            r = await self.client.get(url, headers=headers, params=params, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                return data
            return {"status": "ok", "data": data}
        except httpx.HTTPStatusError as e:
            logger.warning(f"API HTTP {e.response.status_code} for {url}")
            return {"status": "no_data", "code": e.response.status_code}
        except Exception as e:
            logger.warning(f"API error for {url}: {e}")
            return {"status": "no_data"}

    async def close(self):
        try:
            await self.client.aclose()
        except Exception:
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
