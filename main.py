import os
import io
import csv
import json
import base64
import secrets
import random
import smtplib
import traceback
from datetime import datetime, date, timedelta
from collections import Counter
from email.mime.text import MIMEText
import requests

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from bs4 import BeautifulSoup
from sqlalchemy import text, func as sqlfunc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from fastapi import FastAPI, APIRouter, Request, Depends, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse

from sqlmodel import SQLModel, Session, select, func, or_, desc, asc
from groq import Groq

from app.core.config import settings
from app.core.db import init_db
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.modules.database import get_db, engine
from app.modules.data_layer.seed import seed_data
from app.core import billing

from app.modules.auth.router import router as auth_router
from app.core.router import router as core_router
from app.modules.lens_engine.router import router as lens_router

from app.modules.kenyalensiq.router import router as kenyalensiq_router
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

scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)
app = FastAPI(title="EvidLens API", version="2.5.12")

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
    seed_data()
    SQLModel.metadata.create_all(engine)
    print("DB tables checked/created")
    scheduler.add_job(lambda: safe_job(scrape_kpin_prices, "KPIN"), CronTrigger(hour=settings.KPIN_SCRAPE_HOUR, minute=settings.KPIN_SCRAPE_MINUTE), id="kpin_scrape", replace_existing=True)
    scheduler.add_job(lambda: safe_job(fetch_real_news, "NEWS"), CronTrigger(hour=settings.NEWS_SCRAPE_HOUR, minute=settings.NEWS_SCRAPE_MINUTE), id="news_scrape", replace_existing=True)
    scheduler.add_job(lambda: safe_job(fetch_real_tweets, "TWEETS"), CronTrigger(hour=settings.TWEETS_SCRAPE_HOUR, minute=settings.TWEETS_SCRAPE_MINUTE), id="tweets_scrape", replace_existing=True)
    scheduler.start()
    print(f"Scheduler started. Timezone: {settings.SCHEDULER_TIMEZONE}")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    shutdown_scheduler()
    print("Scheduler shut down")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
APP_SUPABASE_KEY = os.getenv("APP_SUPABASE_KEY")
client = Groq(api_key=GROQ_API_KEY)
supabase: Client = None
if SUPABASE_URL and APP_SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, APP_SUPABASE_KEY)

app.include_router(kenyalensiq_router, prefix="/kenyalensiq", tags=["kenyalensiq"])
app.include_router(competitive_router, prefix="/competitive", tags=["Competitive"])
app.include_router(market_router, prefix="/market", tags=["Market"])
app.include_router(location_router, prefix="/location", tags=["Location"])
app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(kb_router, prefix="/kb", tags=["KB"])
app.include_router(reports_router, prefix="/reports", tags=["Reports"])
app.include_router(ai_insights_router, prefix="/ai", tags=["AI Insights"])
app.include_router(business_os_router, prefix="/business", tags=["Business OS"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(rag_router, prefix="/rag", tags=["RAG"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(cron_router, tags=["Cron"])
app.include_router(lens_router, tags=["Lens"])
app.include_router(core_router, tags=["Core"])
app.include_router(storage_router, tags=["Storage"])
app.include_router(chatbot_router)
app.include_router(billing.router)

def get_session():
    with Session(engine) as session:
        yield session

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
