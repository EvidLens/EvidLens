from sqlmodel import Session
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.modules.competitive_engine.service import CompetitiveEngineService
from app.modules.market_engine.service import MarketEngineService
from app.modules.lens_engine.service import LensEngineService
from app.modules.ai_insights.service import AIInsightsService
from app.modules.knowledge_base.service import KnowledgeBaseService

class CronService:
    def __init__(self, db: Session):
        self.db = db
        self.jobs: Dict[str, Any] = {
            "competitive_sync": self.run_competitive_sync,
            "market_sync": self.run_market_sync,
            "lens_refresh": self.run_lens_refresh,
            "ai_insights_refresh": self.run_ai_insights_refresh,
            "kb_index": self.run_kb_index,
            "daily_report": self.run_daily_report
        }

    async def run_job(self, job_name: str):
        if job_name not in self.jobs:
            return {"status": "error", "message": f"Job {job_name} not found"}
        try:
            result = await self.jobs[job_name]()
            return {"status": "success", "job": job_name, "result": result, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"status": "error", "job": job_name, "error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def get_job_response(self, job_name: str):
        return {"status": "queued", "job": job_name, "message": f"Job {job_name} queued for execution"}

    async def run_competitive_sync(self):
        service = CompetitiveEngineService(self.db)
        await service.sync_competitor_data()
        return {"synced": "competitive_data"}

    async def run_market_sync(self):
        service = MarketEngineService(self.db)
        await service.sync_market_funding()
        return {"synced": "market_funding"}

    async def run_lens_refresh(self):
        service = LensEngineService(self.db)
        await service.refresh_all_sectors()
        return {"refreshed": "lens_insights"}

    async def run_ai_insights_refresh(self):
        service = AIInsightsService(self.db)
        await service.generate_daily_insights()
        return {"generated": "ai_insights"}

    async def run_kb_index(self):
        service = KnowledgeBaseService(self.db)
        await service.rebuild_index()
        return {"reindexed": "knowledge_base"}

    async def run_daily_report(self):
        return {"generated": "daily_report", "time": datetime.utcnow().isoformat()}
