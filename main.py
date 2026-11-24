import os
import traceback
from typing import Optional
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import Request
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session
from sqlmodel import select
from sqlmodel import func
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers import SchedulerNotRunningError
from app.core.models import MarketMetric
from app.core.models import Company
from app.core.models import Report
from app.core.models import PriceData
from app.core.models import NewsArticle
from app.core.models import SocialMention
from app.core.models import KnowledgeChunk
from app.core.models import ExportOpportunity
from app.core.models import Competitor
from app.core.config import settings
from app.core.db import init_db
from app.core.db import engine
from app.core.scheduler import start_scheduler
from app.core.scheduler import shutdown_scheduler
from app.modules.auth.models import AuthUser
from app.modules.database import get_session as get_db
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
from app.modules.ai_insights.router import router as ai_insights_router
from app.modules.ai_insights.router import router_api as ai_api_router
from app.modules.business_os.router import router as business_os_router
from app.modules.rag.router import router as rag_router
from app.modules.payments.router import router as payments_router
from app.modules.api.routes import router as api_router
from app.modules.cron.router import router as cron_router
from app.modules.storage.router import router as storage_router
from app.modules.api import data
from app.modules.api import meta
from app.core import billing

load_dotenv()
UTC = timezone.utc
scheduler = AsyncIOScheduler(
    timezone=getattr(
        settings,
        "SCHEDULER_TIMEZONE",
        "Africa/Nairobi"
    )
)
APP_VERSION = "2.6.4"
app = FastAPI(
    title="EvidLens API",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)
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
app.add_middleware(
    AuthMiddleware
)

async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[AuthUser]:
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        user = db.exec(
            select(AuthUser).where(
                AuthUser.id == int(user_id)
            )
        ).first()
        if not user:
            return None
        if not user.is_active:
            return None
        if not user.email_verified:
            return None
        return user
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None

def safe_job(
    job_func,
    job_name: str,
):
    try:
        print(f"[{job_name}] Running...")
        job_func()
        print(f"[{job_name}] Success")
    except Exception as e:
        print(f"[{job_name}] FAILED: {e}")
        traceback.print_exc()

def fix_auth_user_table():
    cols = []
    cols.append("ADD COLUMN IF NOT EXISTS phone VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS full_name VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS hashed_password VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS avatar_url VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS plan VARCHAR DEFAULT 'free'")
    cols.append("ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 0")
    cols.append("ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE")
    cols.append("ADD COLUMN IF NOT EXISTS verification_token VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS reset_token VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP")
    cols.append("ADD COLUMN IF NOT EXISTS sector VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS county VARCHAR")
    cols.append("ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'USER'")
    cols.append("ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
    cols.append("ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT FALSE")
    cols.append("ADD COLUMN IF NOT EXISTS theme VARCHAR DEFAULT 'light'")
    cols.append("ADD COLUMN IF NOT EXISTS language VARCHAR DEFAULT 'en'")
    cols.append("ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")
    cols.append("ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
    try:
        with engine.connect() as conn:
            for sql in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE auth_user {sql}"
                        )
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✓ AUTH_USER MIGRATED")
    except Exception as e:
        print(f"AUTH_USER error: {e}")

def fix_reports_table():
    enum_sqls = []
    enum_sqls.append(
        "ALTER TABLE reports ALTER COLUMN format TYPE VARCHAR(20) USING format::text"
    )
    enum_sqls.append(
        "ALTER TABLE reports ALTER COLUMN status TYPE VARCHAR(50) USING status::text"
    )
    enum_sqls.append(
        "ALTER TABLE reports ALTER COLUMN report_type TYPE VARCHAR(100) USING report_type::text"
    )
    try:
        with engine.connect() as conn:
            for sql in enum_sqls:
                try:
                    conn.execute(
                        text(sql)
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
    except Exception:
        pass
    add_cols = []
    add_cols.append("ADD COLUMN IF NOT EXISTS file_type VARCHAR(20) DEFAULT 'pdf'")
    add_cols.append("ADD COLUMN IF NOT EXISTS file_path VARCHAR(500)")
    add_cols.append("ADD COLUMN IF NOT EXISTS file_size_kb INTEGER")
    add_cols.append("ADD COLUMN IF NOT EXISTS download_count INTEGER DEFAULT 0")
    add_cols.append("ADD COLUMN IF NOT EXISTS is_branded BOOLEAN DEFAULT FALSE")
    add_cols.append("ADD COLUMN IF NOT EXISTS kra_compliant BOOLEAN DEFAULT TRUE")
    add_cols.append("ADD COLUMN IF NOT EXISTS report_metadata JSON DEFAULT '{}'::json")
    add_cols.append("ADD COLUMN IF NOT EXISTS payment_id INTEGER")
    add_cols.append("ADD COLUMN IF NOT EXISTS is_auto_weekly BOOLEAN DEFAULT FALSE")
    add_cols.append("ADD COLUMN IF NOT EXISTS data JSON DEFAULT '{}'::json")
    add_cols.append("ADD COLUMN IF NOT EXISTS error_message TEXT")
    add_cols.append("ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP")
    add_cols.append("ADD COLUMN IF NOT EXISTS county VARCHAR(100)")
    add_cols.append("ADD COLUMN IF NOT EXISTS sub_county VARCHAR(100)")
    add_cols.append("ADD COLUMN IF NOT EXISTS ward VARCHAR(100)")
    add_cols.append("ADD COLUMN IF NOT EXISTS town VARCHAR(100)")
    add_cols.append("ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'Kenya'")
    try:
        with engine.connect() as conn:
            for col in add_cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE reports {col}"
                        )
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✓ REPORTS MIGRATED")
    except Exception as e:
        print(f"REPORTS error: {e}")

def fix_company_table():
    cols = []
    cols.append("ADD COLUMN IF NOT EXISTS rating FLOAT DEFAULT 0")
    cols.append("ADD COLUMN IF NOT EXISTS reviews INTEGER DEFAULT 0")
    cols.append("ADD COLUMN IF NOT EXISTS description TEXT")
    cols.append("ADD COLUMN IF NOT EXISTS lat FLOAT DEFAULT 0")
    cols.append("ADD COLUMN IF NOT EXISTS lng FLOAT DEFAULT 0")
    try:
        with engine.connect() as conn:
            for sql in cols:
                try:
                    conn.execute(
                        text(
                            f"ALTER TABLE company {sql}"
                        )
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✓ COMPANY MIGRATED - rating + reviews added")
    except Exception as e:
        print(f"COMPANY error: {e}")

def fix_export_opportunities_table():
    sqls = []
    sqls.append(
        "ALTER TABLE export_opportunities ALTER COLUMN country SET DEFAULT 'Kenya'"
    )
    sqls.append(
        "ALTER TABLE export_opportunities ALTER COLUMN country DROP NOT NULL"
    )
    sqls.append(
        "ALTER TABLE export_opportunities ALTER COLUMN opportunity_score SET DEFAULT 0"
    )
    sqls.append(
        "ALTER TABLE export_opportunities ALTER COLUMN opportunity_score DROP NOT NULL"
    )
    sqls.append(
        "UPDATE export_opportunities SET country = 'Kenya' WHERE country IS NULL"
    )
    sqls.append(
        "UPDATE export_opportunities SET opportunity_score = 0 WHERE opportunity_score IS NULL"
    )
    try:
        with engine.connect() as conn:
            for sql in sqls:
                try:
                    conn.execute(
                        text(sql)
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
        print("✓ EXPORT_OPPORTUNITIES MIGRATED - country default Kenya")
    except Exception as e:
        print(f"EXPORT_OPPORTUNITIES error: {e}")

def fix_audit_table():
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        action VARCHAR(100),
                        report_id INTEGER,
                        ip VARCHAR(50),
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )
            conn.commit()
        print("✓ AUDIT_LOGS READY")
    except Exception as e:
        print(f"AUDIT error: {e}")

def fix_reports_tenant():
    try:
        with engine.connect() as conn:
            try:
                conn.execute(
                    text(
                        "ALTER TABLE reports ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'public'"
                    )
                )
                conn.commit()
            except Exception:
                conn.rollback()
        print("✓ REPORTS tenant_id READY")
    except Exception as e:
        print(f"REPORTS tenant error: {e}")

def force_create_tables():
    tables = []
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS company (
            id SERIAL PRIMARY KEY,
            name VARCHAR,
            sector VARCHAR,
            county VARCHAR,
            description TEXT,
            rating FLOAT DEFAULT 0,
            reviews INTEGER DEFAULT 0,
            lat FLOAT DEFAULT 0,
            lng FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS market_metrics (
            id SERIAL PRIMARY KEY,
            product VARCHAR,
            county VARCHAR,
            subcounty VARCHAR,
            sector VARCHAR,
            company_name VARCHAR,
            avg_price_kes FLOAT,
            demand_score FLOAT,
            created_at TIMESTAMP DEFAULT NOW(),
            timestamp TIMESTAMP DEFAULT NOW(),
            user_id INTEGER
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS price_data (
            id SERIAL PRIMARY KEY,
            product_name VARCHAR,
            county VARCHAR,
            sector VARCHAR,
            price FLOAT,
            tenant_id VARCHAR,
            timestamp TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY,
            title VARCHAR,
            summary TEXT,
            content TEXT,
            source VARCHAR,
            category VARCHAR,
            url VARCHAR,
            county VARCHAR,
            published_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS social_mentions (
            id SERIAL PRIMARY KEY,
            platform VARCHAR,
            content TEXT,
            author VARCHAR,
            url VARCHAR,
            sentiment VARCHAR,
            county VARCHAR,
            sector VARCHAR,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            title VARCHAR(500),
            report_type VARCHAR(100),
            format VARCHAR(20),
            file_type VARCHAR(20) DEFAULT 'pdf',
            status VARCHAR(50),
            query TEXT,
            sector VARCHAR,
            country VARCHAR,
            county VARCHAR,
            sub_county VARCHAR,
            ward VARCHAR,
            town VARCHAR,
            file_path VARCHAR,
            file_size_kb INTEGER,
            download_count INTEGER DEFAULT 0,
            is_branded BOOLEAN DEFAULT FALSE,
            kra_compliant BOOLEAN DEFAULT TRUE,
            report_metadata JSON,
            payment_id INTEGER,
            is_auto_weekly BOOLEAN DEFAULT FALSE,
            expires_at TIMESTAMP,
            error_message TEXT,
            data JSON,
            tenant_id VARCHAR(100) DEFAULT 'public',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id SERIAL PRIMARY KEY,
            sector VARCHAR,
            county VARCHAR,
            chunk_text TEXT,
            chunk_type VARCHAR,
            source VARCHAR,
            embedding JSON,
            chunk_metadata JSON,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    tables.append(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            action VARCHAR(100),
            report_id INTEGER,
            ip VARCHAR(50),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    try:
        with engine.connect() as conn:
            for sql in tables:
                try:
                    conn.execute(
                        text(sql)
                    )
                except Exception as e:
                    print(f"Table skip: {e}")
            conn.commit()
        print("✓ TABLES ENSURED")
    except Exception as e:
        print(f"Force create failed: {e}")

@app.on_event("startup")
def on_startup():
    try:
        init_db()
        print("✓ DB INIT OK - Core tables created")
    except Exception as e:
        print(f"DB init error: {e}")
        traceback.print_exc()
    try:
        force_create_tables()
    except Exception as e:
        print(f"Force create error: {e}")
    try:
        fix_auth_user_table()
    except Exception as e:
        print(f"Auth migrate error: {e}")
    try:
        fix_reports_table()
    except Exception as e:
        print(f"Reports migrate error: {e}")
    try:
        fix_company_table()
    except Exception as e:
        print(f"Company migrate error: {e}")
    try:
        fix_export_opportunities_table()
    except Exception as e:
        print(f"Export migrate error: {e}")
    try:
        fix_audit_table()
    except Exception as e:
        print(f"Audit migrate error: {e}")
    try:
        fix_reports_tenant()
    except Exception as e:
        print(f"Reports tenant migrate error: {e}")
    try:
        from app.modules.cron.jobs import scrape_kpin_prices
        from app.modules.cron.jobs import fetch_real_news
        from app.modules.cron.jobs import fetch_real_tweets
        scheduler.add_job(
            lambda: safe_job(
                scrape_kpin_prices,
                "KPIN"
            ),
            CronTrigger(
                hour=getattr(
                    settings,
                    "KPIN_SCRAPE_HOUR",
                    3
                ),
                minute=0
            ),
            id="kpin_scrape",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: safe_job(
                fetch_real_news,
                "NEWS"
            ),
            CronTrigger(
                hour=getattr(
                    settings,
                    "NEWS_SCRAPE_HOUR",
                    4
                ),
                minute=0
            ),
            id="news_scrape",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: safe_job(
                fetch_real_tweets,
                "TWEETS"
            ),
            CronTrigger(
                hour=getattr(
                    settings,
                    "TWEETS_SCRAPE_HOUR",
                    5
                ),
                minute=0
            ),
            id="tweets_scrape",
            replace_existing=True,
        )
        scheduler.start()
        print("✓ Scheduler ON - PRODUCTION ONLY, NO SEED")
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

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)
templates = Jinja2Templates(
    directory="app/templates",
    auto_reload=True
)
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

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    return templates.TemplateResponse(
        "privacy.html",
        {
            "request": request
        }
    )

@app.get("/terms", response_class=HTMLResponse)
def terms_page(request: Request):
    return templates.TemplateResponse(
        "terms.html",
        {
            "request": request
        }
    )

@app.get("/dpa", response_class=HTMLResponse)
def dpa_page(request: Request):
    return templates.TemplateResponse(
        "dpa.html",
        {
            "request": request
        }
    )

@app.get("/signup", response_class=HTMLResponse)
def signup_page(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional)
):
    if current_user is not None:
        return RedirectResponse(
            url="/",
            status_code=302
        )
    return templates.TemplateResponse(
        "signup.html",
        {
            "request": request
        }
    )

@app.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional)
):
    if current_user is not None:
        return RedirectResponse(
            url="/",
            status_code=302
        )
    return templates.TemplateResponse(
        "signup.html",
        {
            "request": request
        }
    )

@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional)
):
    if current_user is not None:
        return RedirectResponse(
            url="/",
            status_code=302
        )
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request
        }
    )

@app.get("/signin", response_class=HTMLResponse)
def signin_page(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional)
):
    if current_user is not None:
        return RedirectResponse(
            url="/",
            status_code=302
        )
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request
        }
    )

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        "forgot.html",
        {
            "request": request
        }
    )

@app.get("/forgot", response_class=HTMLResponse)
def forgot_alias_page(request: Request):
    return templates.TemplateResponse(
        "forgot.html",
        {
            "request": request
        }
    )

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request
        }
    )

@app.get("/welcome", response_class=HTMLResponse)
def welcome_page(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional)
):
    if current_user is not None:
        return RedirectResponse(
            url="/",
            status_code=302
        )
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request
        }
    )

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_alias(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional)
):
    if current_user is None:
        return RedirectResponse(
            url="/login",
            status_code=302
        )
    return RedirectResponse(
        url="/",
        status_code=302
    )

@app.get("/", response_class=HTMLResponse)
def root(
    request: Request,
    current_user: Optional[AuthUser] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    if current_user is None:
        return RedirectResponse(
            url="/login",
            status_code=302
        )
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=48)
    real_count = 0
    try:
        real_count = db.exec(
            select(func.count()).select_from(MarketMetric).where(
                MarketMetric.created_at >= cutoff
            )
        ).first() or 0
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        real_count = 0
    API = {}
    API["prices"] = "/api/data/prices"
    API["demand"] = "/api/data/demand"
    API["companies"] = "/api/data/companies"
    API["county_stats"] = "/api/data/county-stats"
    API["sectors"] = "/api/data/sectors"
    API["opportunities"] = "/api/data/opportunities"
    API["analyze"] = "/api/analyze"
    API["chat"] = "/api/chat"
    API["download"] = "/api/download"
    API["export"] = "/api/export"
    API["get_sectors"] = "/api/meta/sectors"
    API["get_counties"] = "/api/meta/counties"
    API["get_subcounties"] = "/api/meta/subcounties"
    API["trending"] = "/analysis/trending"
    API["search"] = "/analysis/search"
    API["logout"] = "/auth/logout"
    API["login"] = "/login"

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

    from app.modules.pricing_engine.models import ProductPrice
    from app.modules.pricing_engine.models import Competitor as PriceCompetitor
    from app.modules.competitive_engine.models import Company as CompCompany
    from app.core.models import KenyaLensBusiness
    c1 = safe_count(
        select(func.count()).select_from(Competitor)
    )
    c2 = safe_count(
        select(func.count()).select_from(PriceCompetitor)
    )
    c3 = safe_count(
        select(func.count()).select_from(CompCompany)
    )
    c4 = safe_count(
        select(func.count()).select_from(KenyaLensBusiness)
    )
    c5 = safe_count(
        select(func.count()).select_from(Company)
    )
    competitor_count = max(c1, c2, c3, c4, c5)
    p1 = safe_count(
        select(func.count()).select_from(PriceData)
    )
    p2 = safe_count(
        select(func.count()).select_from(ProductPrice)
    )
    p3 = safe_count(
        select(func.count()).select_from(MarketMetric)
    )
    price_count = max(p1, p2, p3)
    business_count = safe_count(
        select(func.count()).select_from(Company)
    )
    metric_count = safe_count(
        select(func.count()).select_from(MarketMetric)
    )
    news_count = safe_count(
        select(func.count()).select_from(NewsArticle)
    )
    social_count = safe_count(
        select(func.count()).select_from(SocialMention)
    )
    report_count = safe_count(
        select(func.count()).select_from(Report)
    )
    knowledge_count = safe_count(
        select(func.count()).select_from(KnowledgeChunk)
    )
    export_count = safe_count(
        select(func.count()).select_from(ExportOpportunity)
    )
    county_count = safe_count(
        select(func.count(func.distinct(MarketMetric.county)))
    )
    policy_count = news_count
    modules = []
    modules.append(
        {
            "key": "Competitive Engine",
            "name": "Competitive Engine",
            "route": "/competitive",
            "icon": "🎯",
            "count": competitor_count
        }
    )
    modules.append(
        {
            "key": "Pricing Engine",
            "name": "Price Oracle",
            "route": "/market/prices",
            "icon": "💰",
            "count": price_count
        }
    )
    modules.append(
        {
            "key": "Market Engine",
            "name": "Demand Radar",
            "route": "/market/demand",
            "icon": "📈",
            "count": metric_count
        }
    )
    modules.append(
        {
            "key": "Location Engine",
            "name": "County Mapper",
            "route": "/location/counties",
            "icon": "🗺️",
            "count": county_count
        }
    )
    modules.append(
        {
            "key": "Consumer Engine",
            "name": "Consumer Pulse",
            "route": "/voice",
            "icon": "👥",
            "count": social_count
        }
    )
    modules.append(
        {
            "key": "Core OS",
            "name": "Risk Sentinel",
            "route": "/market/risk",
            "icon": "⚠️",
            "count": news_count
        }
    )
    modules.append(
        {
            "key": "Regulatory Engine",
            "name": "Policy Watch",
            "route": "/kb/policy",
            "icon": "📜",
            "count": policy_count
        }
    )
    modules.append(
        {
            "key": "Core OS",
            "name": "Funding Radar",
            "route": "/reports/funding",
            "icon": "🏦",
            "count": business_count
        }
    )
    modules.append(
        {
            "key": "Business OS",
            "name": "Export Navigator",
            "route": "/market/export",
            "icon": "🚢",
            "count": export_count
        }
    )
    modules.append(
        {
            "key": "Core OS",
            "name": "Knowledge Base",
            "route": "/kb",
            "icon": "📚",
            "count": knowledge_count
        }
    )
    modules.append(
        {
            "key": "Report Builder",
            "name": "Report Builder",
            "route": "/reports",
            "icon": "📑",
            "count": report_count
        }
    )
    modules.append(
        {
            "key": "AI Insights",
            "name": "AI Insights",
            "route": "/ai",
            "icon": "🧠",
            "count": knowledge_count
        }
    )
    data_payload = {}
    data_payload["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    data_payload["stats"] = {
        "insights_generated": metric_count,
        "reports_exported": report_count
    }
    data_payload["modules"] = modules
    data_payload["has_real_data"] = real_count > 0
    data_payload["real_count"] = real_count
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "API": API,
            "data": data_payload,
            "current_user": current_user
        }
    )

@app.post("/api/run-scraper")
def run_scraper():
    from app.modules.cron.jobs import scrape_kpin_prices
    try:
        result = scrape_kpin_prices()
        return {
            "status": "ok",
            "source": "KPIN",
            "result": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "source": "KPIN",
            "error": str(e)
        }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.6.4"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(
        os.getenv(
            "PORT",
            8000
        )
    )
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
