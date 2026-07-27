from app.core.scheduler import init_db, seed_data, start_scheduler, shutdown_scheduler
from app.routers.pages import router as pages_router
from app.modules.analysis.service import router as analysis_router
from app.modules.payments.mpesa import router as mpesa_router
app.include_router(mpesa_router)
app.include_router(pages_router)
app.include_router(analysis_router)
from app.routers.api import router as api_router
app.include_router(api_router)
from app.routers.pages import router as pages_router
app.include_router(pages_router)
from app.modules.core.models import UserSubscription
from datetime import datetime, timedelta
from app.modules.core.service import get_all_pricing

# Standard lib
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

# 3rd party
import pandas as pd
import requests
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from supabase import create_client, Client
from bs4 import BeautifulSoup
from sqlalchemy import text, func as sqlfunc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# FastAPI
from fastapi import FastAPI, APIRouter, Request, Depends, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse

# Pydantic
from pydantic import BaseModel, Field, field_validator

# SQLModel + SQLAlchemy
from sqlmodel import SQLModel, Session, create_engine, select, func, or_, desc, asc, Field as SQLField, Column, JSON

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas

# Groq - ADDED SO client = Groq() WORKS
from groq import Groq

# Your modules - MERGED BLOCK, NO DUPLICATES
from app.core.config import settings

# DB
from app.modules.database import get_db, engine
from app.modules.db import init_db
from app.modules.data_layer.seed import seed_data

# Auth
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user, require_active_subscription
from app.modules.auth.router import router as auth_router
from app.modules.core.service import _core

# KenyaLens Core Models
from app.modules.kenyalensiq.models import (
    MarketMetric, PriceData, NewsArticle, SocialMention,
    KenyaTenant, KenyaLensBusiness, KenyaLensSurvey, KenyaLensResponse,
    KenyaLensSubscription, KenyaLensAlert, KenyaLensMember,
    KenyaLensApiUsage, ExportOpportunity
)

# Lens Engine
from app.modules.lens_engine.service import LensEngineService, scrape_kpin_prices, fetch_real_news, fetch_real_tweets
from app.modules.lens_engine.router import router as lens_router

# All Product Routers
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
from app.modules.core.router import router as core_router
from app.modules.storage.router import router as storage_router
from app.modules.chatbot.router import router as chatbot_router

# Cron
from app.modules.cron.price_cron import start_scheduler

scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)
app = FastAPI(title="EvidLens API", version="2.5.12")

def safe_job(job_func, job_name):
    """Wrapper so 1 job failing doesn't kill others"""
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
    start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    shutdown_scheduler()

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    print("DB tables checked/created")

    # Jobs
    scheduler.add_job(
        lambda: safe_job(scrape_kpin_prices, "KPIN"),
        CronTrigger(hour=settings.KPIN_SCRAPE_HOUR, minute=settings.KPIN_SCRAPE_MINUTE),
        id="kpin_scrape", replace_existing=True
    )
    scheduler.add_job(
        lambda: safe_job(fetch_real_news, "NEWS"),
        CronTrigger(hour=settings.NEWS_SCRAPE_HOUR, minute=settings.NEWS_SCRAPE_MINUTE),
        id="news_scrape", replace_existing=True
    )
    scheduler.add_job(
        lambda: safe_job(fetch_real_tweets, "TWEETS"),
        CronTrigger(hour=settings.TWEETS_SCRAPE_HOUR, minute=settings.TWEETS_SCRAPE_MINUTE),
        id="tweets_scrape", replace_existing=True
    )
    scheduler.start()
    print(f"Scheduler started. Timezone: {settings.SCHEDULER_TIMEZONE}")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("Scheduler shut down")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

AFRICASTALKING_API_KEY = os.getenv("AFRICASTALKING_API_KEY")
AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME")
APP_SUPABASE_KEY = os.getenv("APP_SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ENV = os.getenv("ENV")
FROM_EMAIL = os.getenv("FROM_EMAIL")
FROM_NAME = os.getenv("FROM_NAME")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LOCATIONIQ_KEY = os.getenv("LOCATIONIQ_KEY")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")
MPESA_INITIATOR_NAME = os.getenv("MPESA_INITIATOR_NAME")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_SECURITY_CREDENTIAL = os.getenv("MPESA_SECURITY_CREDENTIAL")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
STORAGE_TYPE = os.getenv("STORAGE_TYPE")
SUPABASE_URL = os.getenv("SUPABASE_URL")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

client = Groq(api_key=GROQ_API_KEY)

supabase: Client = None
if SUPABASE_URL and APP_SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, APP_SUPABASE_KEY)
        print("Supabase connected")
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        supabase = None
else:
    print("Warning: SUPABASE_URL or APP_SUPABASE_KEY not set")
    
app.include_router(kenyalensiq_router)
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
app.include_router(lens_router)
app.include_router(core_router)
app.include_router(storage_router)
app.include_router(chatbot_router)

app.include_router(competitive_router, tags=["Competitive"])
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
app.include_router(kenyalensiq_router, prefix="/kenyalensiq", tags=["kenyalensiq"])

def get_session():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


# ====== DASHBOARD API ======
def dashboard_api(session: Session):
    business_count = session.exec(select(func.count(KenyaLensBusiness.id))).one()
    metric_count = session.exec(select(func.count(MarketMetric.id))).one()
    news_count = session.exec(select(func.count(NewsArticle.id))).one()
    social_count = session.exec(select(func.count(SocialMention.id))).one()
    tenant_count = session.exec(select(func.count(KenyaTenant.id))).one()
    survey_count = session.exec(select(func.count(KenyaLensSurvey.id))).one()
    subscription_count = session.exec(select(func.count(KenyaLensSubscription.id))).one()
    alert_count = session.exec(select(func.count(KenyaLensAlert.id))).one()
    member_count = session.exec(select(func.count(KenyaLensMember.id))).one()
    lens_count = session.exec(select(func.count(KenyaLensSurvey.id))).one()
    company_count = business_count
    search_count = session.exec(select(func.count(MarketMetric.id))).one()
    county_count = session.exec(select(func.count(func.distinct(MarketMetric.county)))).one() if metric_count > 0 else 0
    sector_count = session.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() if metric_count > 0 else 0
    try:
        policy_count = session.exec(select(func.count(NewsArticle.id)).where(NewsArticle.category == "Policy")).one()
    except:
        policy_count = 0
    funding_count = session.exec(select(func.count(KenyaLensBusiness.id)).where(or_(KenyaLensBusiness.sector.ilike("%Financial%"),KenyaLensBusiness.sector.ilike("%Banking%"),KenyaLensBusiness.sector.ilike("%Insurance%"),KenyaLensBusiness.sector.ilike("%SACCO%"),KenyaLensBusiness.sector.ilike("%Microfinance%"),KenyaLensBusiness.sector.ilike("%FinTech%")))).one() if business_count > 0 else 0
    try:
        export_count = session.exec(select(func.count(ExportOpportunity.id))).one()
    except:
        export_count = 0
    modules = [
        {"id": 1, "name": "Competitive Engine", "icon": "🎯", "count": company_count, "route": "/competitive"},
        {"id": 2, "name": "Price Oracle", "icon": "💰", "count": metric_count, "route": "/market/prices"},
        {"id": 3, "name": "Demand Radar", "icon": "📈", "count": search_count, "route": "/market/demand"},
        {"id": 4, "name": "County Mapper", "icon": "🗺️", "count": county_count, "route": "/location/counties"},
        {"id": 5, "name": "Consumer Pulse", "icon": "👥", "count": social_count, "route": "/voice"},
        {"id": 6, "name": "Risk Sentinel", "icon": "⚠️", "count": news_count, "route": "/market/risk"},
        {"id": 7, "name": "Policy Watch", "icon": "📜", "count": policy_count, "route": "/kb/policy"},
        {"id": 8, "name": "Funding Radar", "icon": "🏦", "count": funding_count, "route": "/reports/funding"},
        {"id": 9, "name": "Export Navigator", "icon": "🚢", "count": export_count, "route": "/market/export"},
        {"id": 10, "name": "KenyaLensIQ", "icon": "📊", "count": lens_count, "route": "/kenyalensiq"}
    ]
    stats = {
        "insights_generated": search_count,
        "sectors_covered": sector_count,
        "reports_exported": subscription_count,
        "active_products": metric_count,
        "businesses": business_count,
        "surveys": survey_count,
        "alerts": alert_count,
        "members": member_count
    }
    trending = []
    if metric_count > 0:
        top_demands = session.exec(select(MarketMetric.product, MarketMetric.county, MarketMetric.sector, MarketMetric.demand_score).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score)).limit(3)).all()
        for d in top_demands:
            trending.append({"category": d.sector, "headline": f"{d.product} demand up in {d.county}", "score": d.demand_score, "product": d.product, "county": d.county, "updated": ""})
    return {"stats": stats, "trending": trending, "modules": modules, "last_updated": datetime.utcnow().isoformat()}




# ====== 3. DB SETUP + PLACEHOLDERS ======
engine = create_engine("sqlite:///./evidlens.db", echo=True)
SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def get_current_user(): return User(id=1, email="test@evidlens.co.ke", hashed_password="x", name="Test User")
def get_db(): return next(get_session())
def dashboard_api(session): return {"total_users": 0}
def send_email(to, subject, body): print(f"Email to {to}: {subject}")
def send_sms(to, msg): print(f"SMS to {to}: {msg}")
def send_whatsapp(to, msg): print(f"WA to {to}: {msg}")
def get_password_hash(pw): return "hashed_" + pw
def get_subscription(db, user_id): return db.exec(select(Subscription).where(Subscription.user_id == user_id)).first()
def scrape_kpin_prices(): print("Scraping prices...")
def fetch_real_news(): print("Fetching news...")
def fetch_real_tweets(): print("Fetching tweets...")

# ====== 4. APP + ROUTES ======
app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.post("/api/test-notifications")
def test_notifications(payload: dict):
    to = payload.get("to")
    msg = payload.get("message", "Test from EvidLens")
    send_sms(to, msg)
    send_email(to, "EvidLens Test", f"<p>{msg}</p>")
    send_whatsapp(to, msg)
    return {"status": "sent", "channels": ["sms", "email", "whatsapp"]}

@app.post("/api/test-notifications")
def test_notifications(payload: dict):
    to = payload.get("to")
    msg = payload.get("message", "Test from EvidLens")
    send_sms(to, msg)
    send_email(to, "EvidLens Test", f"<p>{msg}</p>")
    send_whatsapp(to, msg)
    return {"status": "sent", "channels": ["sms", "email", "whatsapp"]}

# ========== DB SETUP ==========
DATABASE_URL = "sqlite:///./evidlens.db" # change to postgres later
engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_geo_data(session) # run once to fill DB

# ========== 1. YOUR SEED LISTS - ONLY FOR SEEDING ==========
KENYA_SECTORS = [
    "Banks", "Microfinance Institutions", "Insurance & HMOs", "Fintechs & Mobile Money",
    "Capital Markets & Investment Banks", "SACCOs", "Retail - Supermarkets & Chains",
    "Retail - Wholesale & Distributors", "FMCG - Food & Beverage", "FMCG - Personal Care & Household",
    "Manufacturing - Food Processing", "Manufacturing - Textiles & Apparel",
    "Manufacturing - Construction Materials", "Manufacturing - Automotive & Assembly",
    "Manufacturing - Pharmaceuticals", "Manufacturing - Chemicals & Plastics",
    "Agribusiness - Crops & Farming", "Agribusiness - Livestock & Dairy",
    "Agribusiness - Horticulture & Flowers", "Agribusiness - Fisheries & Aquaculture",
    "Agribusiness - Agro-processing", "Telcos & ISPs", "Media & Broadcasting",
    "Advertising & Marketing Agencies", "PR & Communications", "Real Estate - Developers",
    "Real Estate - Agents & Brokers", "Real Estate - Property Management",
    "Construction & Infrastructure", "Architecture & Engineering", "Healthcare - Hospitals & Clinics",
    "Healthcare - Pharmacies", "Healthcare - Medical Devices & Pharma",
    "Education - Universities & Colleges", "Education - Primary & Secondary Schools",
    "Education - EdTech & Training", "Logistics & Transport", "E-Commerce & Marketplaces",
    "Hospitality - Hotels & Resorts", "Hospitality - Restaurants & QSR",
    "Tourism & Tour Operators", "Aviation & Airlines", "Maritime & Shipping",
    "Energy - Electricity Generation", "Energy - Oil & Gas", "Energy - Renewable & Solar",
    "Energy - Utilities & Water", "Mining & Minerals", "Government - National Ministries",
    "Government - County Governments", "Government - State Corporations",
    "Government - Regulatory Authorities", "Public Safety & Security", "Defense", "NGOs",
    "INGOs & UN Agencies", "Donors & Development Partners", "Foundations & Philanthropy",
    "Investors - PE & VC", "Investors - Angel & Family Offices", "Professional Services - Law",
    "Professional Services - Consulting", "Professional Services - Accounting & Audit",
    "Professional Services - HR & Recruitment", "ICT & Software Companies",
    "Data Centers & Cloud Services", "Digital Marketing & Creative", "Automotive - Dealerships",
    "Automotive - Parts & Aftermarket", "Automotive - Ride-hailing & Boda",
    "Gaming & Sports", "Entertainment & Events", "Beauty & Wellness",
    "Waste Management & Recycling", "Environmental & Climate Services"
]

KENYA_COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa", "Homa Bay", "Isiolo",
    "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui",
    "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit", "Meru", "Migori",
    "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri",
    "Samburu", "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"
]

KENYA_SUBCOUNTIES = {
    "Mombasa": ["Changamwe", "Jomvu", "Kisauni", "Nyali", "Likoni", "Mvita"],
    "Kwale": ["Msambweni", "Lunga Lunga", "Matuga", "Kinango"],
    "Kilifi": ["Kilifi North", "Kilifi South", "Kaloleni", "Rabai", "Ganze", "Malindi", "Magarini"],
    "Tana River": ["Garsen", "Galole", "Bura"],
    "Lamu": ["Lamu East", "Lamu West"],
    "Taita-Taveta": ["Taveta", "Wundanyi", "Mwatate", "Voi"],
    "Garissa": ["Garissa Township", "Balambala", "Lagdera", "Dadaab", "Fafi", "Ijara"],
    "Wajir": ["Wajir North", "Wajir East", "Tarbaj", "Wajir West", "Eldas", "Wajir South"],
    "Mandera": ["Mandera West", "Banisa", "Mandera North", "Mandera East", "Lafey", "Kutulo"],
    "Marsabit": ["Moyale", "North Horr", "Saku", "Laisamis"],
    "Isiolo": ["Isiolo North", "Isiolo South", "Garba Tulla"],
    "Meru": ["Imenti North", "Imenti South", "Central Imenti", "Buuri", "Tigania East", "Tigania West", "Igembe North", "Igembe South", "Igembe Central"],
    "Tharaka-Nithi": ["Nithi (Chuka/Igambang'ombe)", "Maara", "Tharaka"],
    "Embu": ["Manyatta", "Runyenjes", "Mbeere South (Gachoka)", "Mbeere North (Siakago)"],
    "Kitui": ["Kitui Central", "Kitui West", "Kitui Rural", "Kitui South", "Mutomo", "Mwingi North", "Mwingi Central", "Mwingi West"],
    "Machakos": ["Machakos Town", "Mavoko", "Kathiani", "Matungulu", "Kangundo", "Mwala", "Yatta", "Masinga"],
    "Makueni": ["Makueni", "Mbooni", "Kibwezi West", "Kibwezi East", "Kaiti", "Kilome"],
    "Nyandarua": ["Kinangop", "Kipipiri", "Ol Kalou", "Ol Jorok", "Ndaragwa"],
    "Nyeri": ["Nyeri Town", "Tetu", "Kieni", "Mathira", "Othaya", "Mukurweini"],
    "Kirinyaga": ["Kirinyaga Central", "Kirinyaga East (Gichugu)", "Kirinyaga West (Ndia)", "Mwea East", "Mwea West"],
    "Murang'a": ["Kiharu", "Kangema", "Mathioya", "Kigumo", "Maragwa", "Kandara", "Gatanga"],
    "Kiambu": ["Thika Town", "Ruiru", "Githunguri", "Kiambu", "Kiambaa", "Kabete", "Kikuyu", "Limuru", "Lari", "Gatundu South", "Gatundu North", "Juja"],
    "Turkana": ["Turkana Central", "Turkana North", "Turkana West", "Turkana South", "Turkana East", "Loima"],
    "West Pokot": ["Kapenguria", "Sigor", "Kacheliba", "Pokot South"],
    "Samburu": ["Samburu Central", "Samburu North", "Samburu East"],
    "Trans Nzoia": ["Saboti", "Kiminini", "Cherangany", "Kwanza", "Endebess"],
    "Uasin Gishu": ["Eldoret East", "Eldoret West", "Kesses", "Moiben", "Soy", "Turbo"],
    "Elgeyo-Marakwet": ["Keiyo North", "Keiyo South", "Marakwet East", "Marakwet West"],
    "Nandi": ["Nandi Hills", "Emgwen", "Chesumei", "Aldai", "Mosop", "Nandi Central"],
    "Baringo": ["Baringo Central", "Baringo North", "Baringo South", "Mogotio", "Tiaty", "Eldama Ravine"],
    "Laikipia": ["Laikipia East", "Laikipia West", "Laikipia North", "Nyahururu", "Ol Moran"],
    "Nakuru": ["Nakuru Town East", "Nakuru Town West", "Naivasha", "Gilgil", "Molo", "Njoro", "Kuresoi North", "Kuresoi South", "Rongai", "Subukia"],
    "Narok": ["Narok North", "Narok South", "Narok East", "Narok West", "Transmara West", "Transmara East"],
    "Kajiado": ["Kajiado Central", "Kajiado North", "Kajiado East", "Kajiado West", "Kajiado South"],
    "Kericho": ["Ainamoi", "Belgut", "Bureti", "Kipkelion East", "Kipkelion West", "Soin/Sigowet"],
    "Bomet": ["Bomet Central", "Bomet East", "Chepalungu", "Konoin", "Sotik"],
    "Kakamega": ["Lurambi", "Mumias East", "Mumias West", "Matungu", "Navakholo", "Khwisero", "Butere", "Shinyalu", "Ikolomani", "Lugari", "Likuyani"],
    "Vihiga": ["Vihiga", "Sabatia", "Hamisi", "Emuhaya", "Luanda"],
    "Bungoma": ["Kanduyi", "Bumula", "Kabuchai", "Kimilili", "Mt. Elgon", "Sirisia", "Tongaren", "Webuye East", "Webuye West"],
    "Busia": ["Teso North", "Teso South", "Nambale", "Matayos", "Butula", "Funyula", "Budalangi"],
    "Siaya": ["Alego Usonga", "Gem", "Ugenya", "Ugunja", "Bondo", "Rarieda"],
    "Kisumu": ["Kisumu Central", "Kisumu East", "Kisumu West", "Seme", "Nyando", "Muhoroni", "Nyakach"],
    "Homa Bay": ["Homa Bay Town", "Kasipul", "Kabondo Kasipul", "Karachuonyo", "Rangwe", "Ndhiwa", "Mbita", "Suba"],
    "Migori": ["Migori East", "Migori West", "Rongo", "Awendo", "Uriri", "Nyatike", "Kuria East", "Kuria West"],
    "Kisii": ["Kitutu Chache North", "Kitutu Chache South", "South Mugirango", "Bomachoge Borabu", "Bomachoge Chache", "Bobasi", "Nyaribari Chache", "Nyaribari Masaba", "Bonchari"],
    "Nyamira": ["West Mugirango", "North Mugirango", "Kitutu Masaba", "Borabu"],
    "Nairobi": ["Westlands", "Dagoretti North", "Dagoretti South", "Lang'ata", "Kibra", "Roysambu", "Kasarani", "Ruaraka", "Embakasi North", "Embakasi South", "Embakasi East", "Embakasi West", "Embakasi Central", "Makadara", "Kamukunji", "Starehe", "Mathare"]
}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
