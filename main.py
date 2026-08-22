import os
import traceback
from typing import Optional
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlmodel import func

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from sqlmodel import Session, select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers import SchedulerNotRunningError

from app.core.models import MarketMetric, Company, Report, PriceData, NewsArticle, SocialMention, KnowledgeChunk, ExportOpportunity
from app.modules.api import data, meta
from app.core.config import settings
from app.core.db import init_db, engine
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.modules.auth.models import AuthUser
from app.modules.database import get_session as get_db

from app.modules.auth.router import router as auth_router
from app.modules.auth.dependencies import get_current_user
from app.core.router import router as core_router
from app.modules.competitive_engine.router import router as competitive_router
from app.modules.market_engine.router import router as market_router
from app.modules.location_intel.router import router as location_router
from app.modules.consumer_voice.router import router as voice_router
from app.modules.knowledge_base.router import router as kb_router
from app.modules.report_builder.router import router as reports_router
from app.modules.ai_insights.router import router as ai_insights_router
from app.modules.business_os.router import router as business_os_router
from app.modules.rag.router import router as rag_router
from app.modules.payments.router import router as payments_router
from app.modules.api.routes import router as api_router
from app.modules.cron.router import router as cron_router
from app.modules.storage.router import router as storage_router
from app.modules.chatbot.router import router as chatbot_router
from app.core import billing

load_dotenv()

scheduler = AsyncIOScheduler(timezone=getattr(settings, "SCHEDULER_TIMEZONE", "Africa/Nairobi"))
app = FastAPI(title="EvidLens API", version="2.5.14", docs_url="/docs", redoc_url="/redoc")
UTC = timezone.utc

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.evidlens.co.ke",
        "https://evidlens.co.ke",
        "https://www.evidlens.co.ke",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        user = db.exec(select(AuthUser).where(AuthUser.id == int(user_id))).first()
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None

def safe_job(job_func, job_name):
    try:
        print(f"[{job_name}] Running...")
        job_func()
        print(f"[{job_name}] Success")
    except Exception as e:
        print(f"[{job_name}] FAILED: {e}")
        traceback.print_exc()

@app.on_event("startup")
def on_startup():
    try:
        init_db()
        print("DB tables checked/created - SUCCESS")
    except Exception as e:
        print(f"DB init error: {e}")
        traceback.print_exc()
    try:
        from app.modules.cron.jobs import scrape_kpin_prices, fetch_real_news, fetch_real_tweets
        scheduler.add_job(lambda: safe_job(scrape_kpin_prices, "KPIN"), CronTrigger(hour=getattr(settings, "KPIN_SCRAPE_HOUR", 3), minute=0), id="kpin_scrape", replace_existing=True)
        scheduler.add_job(lambda: safe_job(fetch_real_news, "NEWS"), CronTrigger(hour=getattr(settings, "NEWS_SCRAPE_HOUR", 4), minute=0), id="news_scrape", replace_existing=True)
        scheduler.add_job(lambda: safe_job(fetch_real_tweets, "TWEETS"), CronTrigger(hour=getattr(settings, "TWEETS_SCRAPE_HOUR", 5), minute=0), id="tweets_scrape", replace_existing=True)
        scheduler.start()
        print(f"Scheduler started. Timezone: {getattr(settings, 'SCHEDULER_TIMEZONE', 'Africa/Nairobi')}")
    except Exception as e:
        print(f"Scheduler start skipped: {e}")

@app.on_event("shutdown")
def shutdown_event():
    try:
        if scheduler.running:
            scheduler.shutdown()
    except SchedulerNotRunningError:
        pass
    try:
        shutdown_scheduler()
    except SchedulerNotRunningError:
        pass
    print("Scheduler shut down")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

app.include_router(competitive_router)
app.include_router(market_router)
app.include_router(location_router)
app.include_router(voice_router)
app.include_router(kb_router)
app.include_router(reports_router)
app.include_router(ai_insights_router)
app.include_router(business_os_router)
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(payments_router)
app.include_router(api_router)
app.include_router(cron_router)
app.include_router(core_router)
app.include_router(storage_router)
app.include_router(chatbot_router)
app.include_router(billing.router)
app.include_router(data.router)
app.include_router(meta.router)

@app.get("/", response_class=HTMLResponse)
def root(request: Request, current_user: Optional[AuthUser] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    API = {
        "prices": "/api/data/prices",
        "demand": "/api/data/demand",
        "companies": "/api/data/companies",
        "county_stats": "/api/data/county-stats",
        "sectors": "/api/data/sectors",
        "opportunities": "/api/data/opportunities",
        "analyze": "/api/analyze",
        "chat": "/api/chat",
        "download": "/api/download",
        "export": "/api/export",
        "get_sectors": "/api/meta/sectors",
        "get_counties": "/api/meta/counties",
        "get_subcounties": "/api/meta/subcounties",
        "logout": "/auth/logout",
        "login": "/login"
    }
    def safe_count(stmt):
        try:
            result = db.exec(stmt).first()
            if result is None:
                return 0
            if isinstance(result, (list, tuple)):
                return result[0] or 0
            return result or 0
        except Exception as e:
            print(f"Count failed: {e}")
            return 0

    business_count = safe_count(select(func.count()).select_from(Company))
    metric_count = safe_count(select(func.count()).select_from(MarketMetric))
    news_count = safe_count(select(func.count()).select_from(NewsArticle))
    social_count = safe_count(select(func.count()).select_from(SocialMention))
    report_count = safe_count(select(func.count()).select_from(Report))
    knowledge_count = safe_count(select(func.count()).select_from(KnowledgeChunk))
    export_count = safe_count(select(func.count()).select_from(ExportOpportunity))
    county_count = safe_count(select(func.count(func.distinct(MarketMetric.county))))
    policy_count = safe_count(select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.category == "policy"))

    modules = [
        {"name": "Competitive Engine", "route": "/competitive", "icon": "🎯", "count": business_count},
        {"name": "Price Oracle", "route": "/market/prices", "icon": "💰", "count": metric_count},
        {"name": "Demand Radar", "route": "/market/demand", "icon": "📈", "count": metric_count},
        {"name": "County Mapper", "route": "/location/counties", "icon": "🗺️", "count": county_count},
        {"name": "Consumer Pulse", "route": "/voice", "icon": "👥", "count": social_count},
        {"name": "Risk Sentinel", "route": "/market/risk", "icon": "⚠️", "count": news_count},
        {"name": "Policy Watch", "route": "/kb/policy", "icon": "📜", "count": policy_count},
        {"name": "Funding Radar", "route": "/reports/funding", "icon": "🏦", "count": business_count},
        {"name": "Export Navigator", "route": "/market/export", "icon": "🚢", "count": export_count},
        {"name": "Knowledge Base", "route": "/kb", "icon": "📚", "count": knowledge_count},
        {"name": "Report Builder", "route": "/reports", "icon": "📑", "count": report_count},
        {"name": "AI Insights", "route": "/ai", "icon": "🧠", "count": knowledge_count},
    ]
    data_payload = {
        "last_updated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
        "stats": {"insights_generated": metric_count, "reports_exported": report_count},
        "modules": modules
    }
    return templates.TemplateResponse("dashboard.html", {"request": request, "API": API, "data": data_payload, "current_user": current_user})

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.5.14"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
