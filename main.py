"""
EvidLens API - Main Application
Version: 2.5.14
Author: EvidLens Engineering
Fixes:
    - file_type column added to reports
    - ENUM reportformat -> VARCHAR (PDF vs pdf crash)
    - InFailedSqlTransaction fixed
"""

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
from starlette.middleware.sessions import SessionMiddleware

from sqlmodel import Session, select, func
from sqlalchemy import text

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers import SchedulerNotRunningError

# ------------------------------------------------------------------
# Core - Models & Config
# ------------------------------------------------------------------
from app.core.models import (
    MarketMetric,
    Company,
    Report,
    PriceData,
    NewsArticle,
    SocialMention,
    KnowledgeChunk,
    ExportOpportunity,
    Competitor,
)
from app.core.config import settings
from app.core.db import init_db, engine
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.modules.auth.models import AuthUser
from app.modules.database import get_session as get_db

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
from app.routers.pages import router as pages_router
from app.modules.data_layer.router import router as data_router
from app.modules.billing.router import router as billing_page_router
from app.modules.analysis.router import router as analysis_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.middleware import AuthMiddleware
from app.core.router import router as core_router
from app.modules.competitive_engine.router import router as competitive_router
from app.modules.market_engine.router import router as market_router
from app.modules.location_intel.router import router as location_router
from app.modules.consumer_voice.router import router as voice_router
from app.modules.knowledge_base.router import router as kb_router
from app.modules.report_builder.router import router as reports_router
from app.modules.ai_insights.router import router as ai_insights_router, router_api as ai_api_router
from app.modules.business_os.router import router as business_os_router
from app.modules.rag.router import router as rag_router
from app.modules.payments.router import router as payments_router
from app.modules.api.routes import router as api_router
from app.modules.cron.router import router as cron_router
from app.modules.storage.router import router as storage_router
from app.modules.api import data, meta
from app.core import billing

# ------------------------------------------------------------------
# Env & Constants
# ------------------------------------------------------------------
load_dotenv()

UTC = timezone.utc

scheduler = AsyncIOScheduler(
    timezone=getattr(settings, "SCHEDULER_TIMEZONE", "Africa/Nairobi")
)

# ------------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------------
app = FastAPI(
    title="EvidLens API",
    version="2.5.14",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SECRET_KEY",
        "evidlens-secret-key-change-2026-strong-random"
    ),
    same_site="lax",
    https_only=True,
)

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

app.add_middleware(AuthMiddleware)

# ==================================================================
# Helpers
# ==================================================================
async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[AuthUser]:
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        user = db.exec(
            select(AuthUser).where(AuthUser.id == int(user_id))
        ).first()
        if not user or not user.is_active or not user.email_verified:
            return None
        return user
    except Exception:
        return None

def safe_job(job_func, job_name: str):
    try:
        print(f"[{job_name}] Running...")
        job_func()
        print(f"[{job_name}] Success")
    except Exception as e:
        print(f"[{job_name}] FAILED: {e}")
        traceback.print_exc()

# ==================================================================
# Database Migrations (Production Safe)
# ==================================================================
def fix_auth_user_table():
    cols = [
        "ADD COLUMN IF NOT EXISTS phone VARCHAR",
        "ADD COLUMN IF NOT EXISTS full_name VARCHAR",
        "ADD COLUMN IF NOT EXISTS hashed_password VARCHAR",
        "ADD COLUMN IF NOT EXISTS avatar_url VARCHAR",
        "ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'free'",
        "ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS verification_token VARCHAR",
        "ADD COLUMN IF NOT EXISTS reset_token VARCHAR",
        "ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP",
        "ADD COLUMN IF NOT EXISTS sector VARCHAR",
        "ADD COLUMN IF NOT EXISTS county VARCHAR",
        "ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'USER'",
        "ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS theme VARCHAR DEFAULT 'light'",
        "ADD COLUMN IF NOT EXISTS language VARCHAR DEFAULT 'en'",
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
        "ADD COLUMN IF NOT EXISTS last_login TIMESTAMP",
    ]
    try:
        with engine.connect() as conn:
            for sql in cols:
                try:
                    conn.execute(text(f"ALTER TABLE auth_user {sql}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✓ AUTH_USER MIGRATED")
    except Exception as e:
        print(f"AUTH_USER error: {e}")

def fix_reports_table():
    # 1. Convert ENUM -> VARCHAR (critical fix)
    enum_sqls = [
        "ALTER TABLE reports ALTER COLUMN format TYPE VARCHAR(20) USING format::text",
        "ALTER TABLE reports ALTER COLUMN status TYPE VARCHAR(50) USING status::text",
        "ALTER TABLE reports ALTER COLUMN report_type TYPE VARCHAR(100) USING report_type::text",
    ]
    try:
        with engine.connect() as conn:
            for sql in enum_sqls:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception:
                    conn.rollback()
    except Exception:
        pass

    # 2. Add missing columns
    add_cols = [
        "ADD COLUMN IF NOT EXISTS file_type VARCHAR(20) DEFAULT 'pdf'",
        "ADD COLUMN IF NOT EXISTS file_path VARCHAR(500)",
        "ADD COLUMN IF NOT EXISTS file_size_kb INTEGER",
        "ADD COLUMN IF NOT EXISTS download_count INTEGER DEFAULT 0",
        "ADD COLUMN IF NOT EXISTS is_branded BOOLEAN DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS kra_compliant BOOLEAN DEFAULT TRUE",
        "ADD COLUMN IF NOT EXISTS report_metadata JSON DEFAULT '{}'::json",
        "ADD COLUMN IF NOT EXISTS payment_id INTEGER",
        "ADD COLUMN IF NOT EXISTS is_auto_weekly BOOLEAN DEFAULT FALSE",
        "ADD COLUMN IF NOT EXISTS data JSON DEFAULT '{}'::json",
        "ADD COLUMN IF NOT EXISTS error_message TEXT",
        "ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP",
        "ADD COLUMN IF NOT EXISTS county VARCHAR(100)",
        "ADD COLUMN IF NOT EXISTS sub_county VARCHAR(100)",
        "ADD COLUMN IF NOT EXISTS ward VARCHAR(100)",
        "ADD COLUMN IF NOT EXISTS town VARCHAR(100)",
        "ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'Kenya'",
    ]
    try:
        with engine.connect() as conn:
            for col in add_cols:
                try:
                    conn.execute(text(f"ALTER TABLE reports {col}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✓ REPORTS MIGRATED")
    except Exception as e:
        print(f"REPORTS error: {e}")

def force_create_tables():
    tables = [
        """
        CREATE TABLE IF NOT EXISTS company (
            id SERIAL PRIMARY KEY,
            name VARCHAR, sector VARCHAR, county VARCHAR,
            description TEXT, created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS market_metrics (
            id SERIAL PRIMARY KEY, product VARCHAR, county VARCHAR,
            subcounty VARCHAR, sector VARCHAR, company_name VARCHAR,
            avg_price_kes FLOAT, demand_score FLOAT,
            created_at TIMESTAMP DEFAULT NOW(),
            timestamp TIMESTAMP DEFAULT NOW(), user_id INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS price_data (
            id SERIAL PRIMARY KEY, product_name VARCHAR, county VARCHAR,
            sector VARCHAR, price FLOAT, tenant_id VARCHAR,
            timestamp TIMESTAMP DEFAULT NOW(), created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY, title VARCHAR, summary TEXT,
            content TEXT, source VARCHAR, category VARCHAR,
            url VARCHAR, county VARCHAR,
            published_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS social_mentions (
            id SERIAL PRIMARY KEY, platform VARCHAR, content TEXT,
            author VARCHAR, url VARCHAR, sentiment VARCHAR,
            county VARCHAR, sector VARCHAR, created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY, user_id INTEGER, title VARCHAR(500),
            report_type VARCHAR(100), format VARCHAR(20),
            file_type VARCHAR(20) DEFAULT 'pdf', status VARCHAR(50),
            query TEXT, sector VARCHAR, country VARCHAR, county VARCHAR,
            sub_county VARCHAR, ward VARCHAR, town VARCHAR,
            file_path VARCHAR, file_size_kb INTEGER,
            download_count INTEGER DEFAULT 0,
            is_branded BOOLEAN DEFAULT FALSE,
            kra_compliant BOOLEAN DEFAULT TRUE,
            report_metadata JSON, payment_id INTEGER,
            is_auto_weekly BOOLEAN DEFAULT FALSE,
            expires_at TIMESTAMP, error_message TEXT,
            data JSON, created_at TIMESTAMP DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY, sector VARCHAR, county VARCHAR,
            chunk_text TEXT, chunk_type VARCHAR, source VARCHAR,
            embedding JSON, chunk_metadata JSON,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
    ]
    try:
        with engine.connect() as conn:
            for sql in tables:
                try:
                    conn.execute(text(sql))
                except Exception as e:
                    print(f"Table skip: {e}")
            conn.commit()
        print("✓ TABLES ENSURED")
    except Exception as e:
        print(f"Force create failed: {e}")

# ==================================================================
# Lifecycle
# ==================================================================
@app.on_event("startup")
def on_startup():
    fix_auth_user_table()
    force_create_tables()
    fix_reports_table()

    try:
        init_db()
        print("✓ DB INIT OK")
    except Exception as e:
        print(f"DB init: {e}")

    try:
        from app.modules.cron.jobs import (
            scrape_kpin_prices,
            fetch_real_news,
            fetch_real_tweets,
        )

        scheduler.add_job(
            lambda: safe_job(scrape_kpin_prices, "KPIN"),
            CronTrigger(hour=getattr(settings, "KPIN_SCRAPE_HOUR", 3), minute=0),
            id="kpin_scrape",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: safe_job(fetch_real_news, "NEWS"),
            CronTrigger(hour=getattr(settings, "NEWS_SCRAPE_HOUR", 4), minute=0),
            id="news_scrape",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: safe_job(fetch_real_tweets, "TWEETS"),
            CronTrigger(hour=getattr(settings, "TWEETS_SCRAPE_HOUR", 5), minute=0),
            id="tweets_scrape",
            replace_existing=True,
        )
        scheduler.start()
        print("✓ Scheduler ON")
    except Exception as e:
        print(f"Scheduler skip: {e}")

@app.on_event("shutdown")
def shutdown_event():
    try:
        if scheduler.running:
            scheduler.shutdown()
    except SchedulerNotRunningError:
        pass
    try:
        shutdown_scheduler()
    except Exception:
        pass

# ==================================================================
# Static & Templates
# ==================================================================
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

# ==================================================================
# Register All Routers
# ==================================================================
app.include_router(pages_router)
app.include_router(data_router)
app.include_router(billing_page_router)
app.include_router(competitive_router)
app.include_router(market_router)
app.include_router(location_router)
app.include_router(voice_router)
app.include_router(kb_router)
app.include_router(reports_router)
app.include_router(ai_insights_router)
app.include_router(ai_api_router)
app.include_router(business_os_router)
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(payments_router)
app.include_router(api_router)
app.include_router(cron_router)
app.include_router(core_router)
app.include_router(storage_router)
app.include_router(billing.router)
app.include_router(data.router)
app.include_router(meta.router)
app.include_router(analysis_router)

# ==================================================================
# Public Pages
# ==================================================================
@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

@app.get("/dpa", response_class=HTMLResponse)
def dpa_page(request: Request):
    return templates.TemplateResponse("dpa.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signin", response_class=HTMLResponse)
def signin_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot.html", {"request": request})

@app.get("/forgot", response_class=HTMLResponse)
def forgot_alias_page(request: Request):
    return templates.TemplateResponse("forgot.html", {"request": request})

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})

# ==================================================================
# Dashboard + Health
# ==================================================================
@app.get("/", response_class=HTMLResponse)
def root(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
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
        "trending": "/analysis/trending",
        "search": "/analysis/search",
        "logout": "/auth/logout",
        "login": "/login",
    }

    def safe_count(stmt):
        try:
            result = db.exec(stmt).first()
            if result is None:
                return 0
            if isinstance(result, (list, tuple)):
                return result[0] or 0
            return result or 0
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            return 0

    business_count = safe_count(select(func.count()).select_from(Company))
    metric_count = safe_count(select(func.count()).select_from(MarketMetric))
    price_count = safe_count(select(func.count()).select_from(PriceData))
    competitor_count = safe_count(select(func.count()).select_from(Competitor))
    news_count = safe_count(select(func.count()).select_from(NewsArticle))
    social_count = safe_count(select(func.count()).select_from(SocialMention))
    report_count = safe_count(select(func.count()).select_from(Report))
    knowledge_count = safe_count(select(func.count()).select_from(KnowledgeChunk))
    export_count = safe_count(select(func.count()).select_from(ExportOpportunity))
    county_count = safe_count(
        select(func.count(func.distinct(MarketMetric.county)))
    )

   modules = [
    {
        "key": "Competitive Engine",
        "name": "Competitive Engine",
        "route": "/competitive",
        "icon": "🎯",
        "count": competitor_count,
        "live": competitor_count,
    },
    {
        "key": "Pricing Engine",
        "name": "Price Oracle",
        "route": "/market/prices",
        "icon": "💰",
        "count": price_count,
        "live": price_count,
    },
    {
        "key": "Market Engine",
        "name": "Demand Radar",
        "route": "/market/demand",
        "icon": "📈",
        "count": metric_count,
        "live": metric_count,
    },
    {
        "key": "Location Engine",
        "name": "County Mapper",
        "route": "/location/counties",
        "icon": "🗺️",
        "count": county_count,
        "live": county_count,
    },
    {
        "key": "Consumer Engine",
        "name": "Consumer Pulse",
        "route": "/voice",
        "icon": "👥",
        "count": social_count,
        "live": social_count,
    },
    {
        "key": "Core OS",
        "name": "Risk Sentinel",
        "route": "/market/risk",
        "icon": "⚠️",
        "count": news_count,
        "live": news_count,
    },
    {
        "key": "Regulatory Engine",
        "name": "Policy Watch",
        "route": "/kb/policy",
        "icon": "📜",
        "count": policy_count,
        "live": policy_count,
    },
    {
        "key": "Core OS",
        "name": "Funding Radar",
        "route": "/reports/funding",
        "icon": "🏦",
        "count": business_count,
        "live": business_count,
    },
    {
        "key": "Business OS",
        "name": "Export Navigator",
        "route": "/market/export",
        "icon": "🚢",
        "count": export_count,
        "live": export_count,
    },
    {
        "key": "Core OS",
        "name": "Knowledge Base",
        "route": "/kb",
        "icon": "📚",
        "count": knowledge_count,
        "live": knowledge_count,
    },
    {
        "key": "Report Builder",
        "name": "Report Builder",
        "route": "/reports",
        "icon": "📑",
        "count": report_count,
        "live": report_count,
    },
    {
        "key": "AI Insights",
        "name": "AI Insights",
        "route": "/ai",
        "icon": "🧠",
        "count": knowledge_count,
        "live": knowledge_count,
    },
]

    data_payload = {
        "last_updated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
        "stats": {
            "insights_generated": metric_count,
            "reports_exported": report_count,
        },
        "modules": modules,
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "API": API,
            "data": data_payload,
            "current_user": current_user,
        },
    )

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.5.14"}

# ==================================================================
# Entry
# ==================================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
