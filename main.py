import os
import traceback
from typing import Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from sqlmodel import SQLModel, Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.db import init_db, engine
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.core.models import User

from app.modules.auth.router import router as auth_router
from app.modules.auth.dependencies import get_current_user_optional
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
app = FastAPI(title="EvidLens API", version="2.5.13", docs_url="/docs", redoc_url="/redoc")

UTC = timezone.utc

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
    init_db()
    SQLModel.metadata.create_all(engine)
    print("DB tables checked/created")
    from app.modules.cron.jobs import scrape_kpin_prices, fetch_real_news, fetch_real_tweets
    scheduler.add_job(lambda: safe_job(scrape_kpin_prices, "KPIN"), CronTrigger(hour=getattr(settings, "KPIN_SCRAPE_HOUR", 3), minute=0), id="kpin_scrape", replace_existing=True)
    scheduler.add_job(lambda: safe_job(fetch_real_news, "NEWS"), CronTrigger(hour=getattr(settings, "NEWS_SCRAPE_HOUR", 4), minute=0), id="news_scrape", replace_existing=True)
    scheduler.add_job(lambda: safe_job(fetch_real_tweets, "TWEETS"), CronTrigger(hour=getattr(settings, "TWEETS_SCRAPE_HOUR", 5), minute=0), id="tweets_scrape", replace_existing=True)
    scheduler.start()
    print(f"Scheduler started. Timezone: {getattr(settings, 'SCHEDULER_TIMEZONE', 'Africa/Nairobi')}")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    shutdown_scheduler()
    print("Scheduler shut down")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
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

@app.get("/", response_class=HTMLResponse)
def root(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "now": datetime.now(UTC),
        "current_user": current_user
    })

def get_session():
    with Session(engine) as session:
        yield session

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
