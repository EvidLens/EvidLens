# Standard lib
from io import BytesIO
import os
import statistics
import smtplib
import json
from datetime import datetime, timedelta
from collections import Counter

# 3rd party
from sqlalchemy import text
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client, Client
from bs4 import BeautifulSoup
# import tweepy

# FastAPI
from fastapi import FastAPI, APIRouter, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse

# Pydantic
from pydantic import BaseModel, Field, field_validator

# SQLModel + SQLAlchemy
from sqlmodel import SQLModel, Session, create_engine, select, func, or_, desc, asc, Field, Column, JSON
from sqlalchemy import func as sqlfunc

# ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas

# Email
from email.mime.text import MIMEText

# Your modules
from app.modules.database import get_db
from app.modules.kenyalensiq.models import KenyaLensBusiness, MarketMetric

from app.modules.kenyalensiq.models import (
    MarketMetric, PriceData, NewsArticle, SocialMention,
    KenyaTenant, KenyaLensBusiness, KenyaLensSurvey,
    KenyaLensSubscription, KenyaLensAlert, KenyaLensMember
)

import os
import csv
import io
import base64
import random
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from groq import Groq
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, date, timedelta

from app.modules.kenyalensiq.models import (
    KenyaTenant,
    KenyaLensBusiness,
    KenyaLensSurvey,
    KenyaLensResponse,
    KenyaLensSubscription,
    KenyaLensAlert,
    KenyaLensMember,
    KenyaLensApiUsage,
    ExportOpportunity
)
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user

load_dotenv()

from app.modules.database import engine, create_db_and_tables
from app.modules.db import init_db
from app.modules.data_layer.seed import seed_data
from app.modules.cron.price_cron import start_scheduler
from app.modules.kenyalensiq.router import router as kenyalensiq_router
from app.modules.auth.dependencies import require_active_subscription
from app.modules.competitive_engine.router import router as competitive_router
from app.modules.market_engine.router import router as market_router
from app.modules.location_intel.router import router as location_router
from app.modules.consumer_voice.router import router as voice_router
from app.modules.knowledge_base.router import router as kb_router
from app.modules.report_builder.router import router as reports_router
from app.modules.ai_insights.router import router as ai_insights_router
from app.modules.business_os.router import router as business_os_router
from app.modules.auth.router import router as auth_router
from app.modules.rag.router import router as rag_router
from app.modules.payments.router import router as payments_router
from app.modules.api.routes import router as api_router
from app.modules.cron.router import router as cron_router
from app.modules.lens_engine.router import router as lens_router
from app.modules.core.router import router as core_router
from app.modules.storage.router import router as storage_router
from app.modules.chatbot.router import router as chatbot_router

scheduler = AsyncIOScheduler()

app = FastAPI(title="EvidLens API", version="2.5.12")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    print("DB tables checked/created")

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
SUPABASE_URL = os.getenv("SUPABASE_URL")
APP_SUPABASE_KEY = os.getenv("APP_SUPABASE_KEY")

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

get_db = get_session

def send_sms(to: str, message: str):
    if not AFRICASTALKING_API_KEY: return
    url = "https://api.africastalking.com/version1/messaging"
    headers = {"apiKey": AFRICASTALKING_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    data = {"username": AFRICASTALKING_USERNAME, "to": to, "message": message}
    requests.post(url, data=data, headers=headers)

def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY: return
    requests.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {RESEND_API_KEY}"}, json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [to], "subject": subject, "html": html})

def send_whatsapp(to: str, message: str):
    if not WHATSAPP_TOKEN: return
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}}
    requests.post(url, json=data, headers=headers)

def get_lat_lng(county: str):
    if not LOCATIONIQ_KEY: return None, None
    r = requests.get(f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_KEY}&q={county},Kenya&format=json")
    if r.status_code == 200 and r.json():
        return r.json()[0]["lat"], r.json()[0]["lon"]
    return None, None

def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.cookies.get("user_id") or 1
    return int(user_id)

def get_subscription(db: Session, user_id: int):
    return db.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == user_id)).first()

def get_queries_today(db: Session, user_id: int):
    return len(db.exec(select(KenyaLensApiUsage).where(KenyaLensApiUsage.user_id == user_id, KenyaLensApiUsage.date == date.today())).all())

def log_query(db: Session, user_id: int):
    db.add(KenyaLensApiUsage(user_id=user_id, date=date.today()))
    db.commit()

def check_subscription(user_id: int, db: Session):
    sub = get_subscription(db, user_id)
    if not sub or sub.status!= "active" or sub.expires_at < datetime.utcnow():
        if get_queries_today(db, user_id) >= 3:
            raise HTTPException(status_code=402, detail="Subscribe to continue. 3 free queries used.")
    return True

def send_support_ticket(subject: str, body: str, user_email: str = "user@evidlens.co.ke"):
    """Raises a ticket to support@evidlens.co.ke"""
    try:
        msg = MIMEText(f"From: {user_email}\n\n{body}")
        msg['Subject'] = f"[EvidLens Ticket] {subject}"
        msg['From'] = user_email
        msg['To'] = SUPPORT_EMAIL

        with smtplib.SMTP("smtp.gmail.com", 587) as server: # use env vars on Render
            server.starttls()
            server.login("support@evidlens.co.ke", "your_app_password") # SMTP_USER, SMTP_PASS
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Ticket Error: {e}")
        return False

def generate_insights(user_message: str, user_email: str = "user@evidlens.co.ke", db: Session = Depends(get_db)):
    try:
        # 1. PULL REAL DATA
        top_counties = db.exec(
            select(KenyaLensBusiness.county, func.count(KenyaLensBusiness.id))
          .group_by(KenyaLensBusiness.county)
          .order_by(func.count(KenyaLensBusiness.id).desc())
          .limit(5)
        ).all()

        avg_prices = db.exec(
            select(MarketMetric.sector, func.avg(MarketMetric.metric_value))
          .filter(MarketMetric.metric_type == "price_avg")
          .group_by(MarketMetric.sector)
          .limit(10)
        ).all()

        context = f"""
        REAL DATA CONTEXT:
        Top Counties by Business: {top_counties}
        Avg Prices KES: {avg_prices}
        APP FEATURES: /api/competitive, /api/price-oracle, /api/demand, /api/county, /api/consumer, /report-builder, /ai-insights
        SUPPORT: support@evidlens.co.ke
        Currency: KES. Location: Kenya Counties only.
        """

        system_prompt = """You are EvidLens AI. You give market insights for Kenyan farmers and SMEs.
        Rules:
        1. Be concise. Max 4 sentences. Data-driven. Use KES and Counties.
        2. If user asks "how do I...", guide them step by step through the app features.
        3. If user says "problem", "bug", "not working", "help", "support" -> You MUST offer to raise a ticket to support@evidlens.co.ke. End with: "Should I raise a ticket for you?"
        4. If no data, say "No data yet for X county".
        5. Always give 1 actionable next step.
        """

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt + context},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            max_tokens=350,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "raise_ticket",
                        "description": "Raise a support ticket to EvidLens team at support@evidlens.co.ke",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "subject": {"type": "string", "description": "Short issue title"},
                                "description": {"type": "string", "description": "Full problem description"}
                            },
                            "required": ["subject", "description"]
                        }
                    }
                }
            ]
        )

        response = completion.choices[0].message

        # 2. HANDLE FUNCTION CALL
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.function.name == "raise_ticket":
                    args = json.loads(tool_call.function.arguments)
                    sent = send_support_ticket(args['subject'], args['description'], user_email)
                    if sent:
                        return "Ticket raised successfully. Our team at support@evidlens.co.ke will reply within 24hrs."
                    else:
                        return "Could not send ticket. Please email us directly at support@evidlens.co.ke"

        return response.content

    except Exception as e:
        return f"EvidLens AI Error: {str(e)}. Email support@evidlens.co.ke for support."

def apply_sort(q, model, sort_by: str, order: str):
    if not sort_by or not hasattr(model, sort_by):
        return q
    col = getattr(model, sort_by)
    return q.order_by(desc(col) if order == "desc" else asc(col))

def scrape_kpin_prices():
    url = "https://www.kpin.go.ke/market-prices"
    session = Session(engine)
    try:
        r = requests.get(url, timeout=30)
        df = pd.read_html(r.text)[0]
        df.columns = ['date', 'county', 'market', 'product', 'price', 'unit']
        df['price'] = df['price'].str.replace(',', '').astype(float)
        for _, row in df.iterrows():
            lat, lng = get_lat_lng(row['county'])
            existing = session.exec(select(MarketMetric).where(MarketMetric.product == row['product'], MarketMetric.company_name == row['market'], func.date(MarketMetric.created_at) == datetime.utcnow().date())).first()
            if not existing:
                session.add(MarketMetric(product=row['product'], company_name=row['market'], avg_price_kes=row['price'], county=row['county'], sector=row['unit']))
        session.commit()
    except Exception:
        pass
    finally:
        session.close()

def fetch_real_news():
    if not NEWS_API_KEY: return
    db = Session(engine)
    url = f"https://newsapi.org/v2/everything?q=Kenya&language=en&pageSize=100&apiKey={NEWS_API_KEY}"
    r = requests.get(url, timeout=30)
    data = r.json()
    for article in data.get("articles", []):
        existing = db.exec(select(NewsArticle).where(NewsArticle.title == article["title"])).first()
        if not existing:
            db.add(NewsArticle(title=article["title"], source=article["source"]["name"], summary=article["description"]))
    db.commit()
    db.close()

def fetch_real_tweets():
    if not X_BEARER_TOKEN: return
    db = Session(engine)
    client_t = tweepy.Client(bearer_token=X_BEARER_TOKEN)
    queries = ["Kenya price", "Kenya maize", "Kenya fuel"]
    for query in queries:
        tweets = client_t.search_recent_tweets(query=query, max_results=100)
        if tweets.data:
            for t in tweets.data:
                existing = db.exec(select(SocialMention).where(SocialMention.text == t.text)).first()
                if not existing:
                    db.add(SocialMention(text=t.text, platform="Twitter"))
    db.commit()
    db.close()

@app.on_event("startup")
def on_startup():
    init_db()
    create_db_and_tables()
    seed_data()
    start_scheduler()
    scheduler.add_job(scrape_kpin_prices, "cron", hour="0,6,12,18")
    scheduler.add_job(fetch_real_news, "interval", hours=6)
    scheduler.add_job(fetch_real_tweets, "interval", hours=3)
    scheduler.start()

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

@app.get("/market/risk")
def risk_sentinel(session: Session = Depends(get_session)):
    news = session.exec(select(NewsArticle.id, NewsArticle.title, NewsArticle.source, NewsArticle.summary, NewsArticle.published_at).order_by(NewsArticle.published_at.desc()).limit(10)).all()
    return {"risk_alerts": [dict(n._mapping) for n in news]}

@app.get("/market/export")
def export_navigator(session: Session = Depends(get_session)):
    exports = session.exec(select(ExportOpportunity).limit(20)).all()
    return {"export_opportunities": [e.dict() for e in exports]}

@app.post("/chat")
async def chat(payload: dict, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    check_subscription(user_id, db)
    db.add(MarketMetric(product=payload["message"], county="Kenya", sector="All", demand_score=random.randint(50,100)))
    db.commit()
    ai_response = generate_insights(payload["message"])
    log_query(db, user_id)
    return {"response": ai_response}

@app.get("/api/sectors")
def get_sectors(search: str = "", session: Session = Depends(get_session)):
    q = select(func.distinct(MarketMetric.sector))
    if search:
        q = q.where(MarketMetric.sector.contains(search))
    return {"sectors": [s[0] for s in session.exec(q).all() if s[0]]}

@app.get("/api/counties")
def get_counties(search: str = "", session: Session = Depends(get_session)):
    q = select(func.distinct(MarketMetric.county))
    if search:
        q = q.where(MarketMetric.county.contains(search))
    return {"counties": [c[0] for c in session.exec(q).all() if c[0]]}

@app.get("/api/subcounties")
def get_subcounties(county: str = "", search: str = "", session: Session = Depends(get_session)):
    return {"subcounties": []}

@app.get("/api/products")
def get_products(search: str = "", session: Session = Depends(get_session)):
    q = select(func.distinct(MarketMetric.product))
    if search:
        q = q.where(MarketMetric.product.contains(search))
    return {"products": [p[0] for p in session.exec(q).all() if p[0]]}

@app.get("/api/companies")
def get_companies(search: str = "", sector: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "id", order: str = "desc", session: Session = Depends(get_session)):
    q = select(KenyaLensBusiness)
    if search:
        q = q.where(or_(KenyaLensBusiness.name.ilike(f"%{search}%"), KenyaLensBusiness.sector.ilike(f"%{search}%"), KenyaLensBusiness.county.ilike(f"%{search}%")))
    if sector:
        q = q.where(KenyaLensBusiness.sector == sector)
    if county:
        q = q.where(KenyaLensBusiness.county == county)
    all_data = session.exec(q).all()
    total = len(all_data)
    q = apply_sort(q, KenyaLensBusiness, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": [c.dict() for c in data], "total": total, "page": page}

@app.get("/api/prices")
def get_prices(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "avg_price_kes", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search:
        q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product:
        q = q.where(MarketMetric.product == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"prices": [p.dict() for p in data], "total": total, "page": page}

@app.get("/api/demand")
def get_demand(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search:
        q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product:
        q = q.where(MarketMetric.product == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"demand": [m.dict() for m in data], "total": total, "page": page}

@app.get("/api/county-stats")
def get_county_stats(search: str = "", page: int = 1, limit: int = 47, sort_by: str = "market_size", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric.county, func.sum(MarketMetric.avg_price_kes).label("market_size"), func.avg(MarketMetric.demand_score).label("growth"), func.count(MarketMetric.id).label("volume")).group_by(MarketMetric.county)
    if search:
        q = q.where(MarketMetric.county.contains(search))
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    stats = [dict(r._mapping) for r in data]
    stats.sort(key=lambda x: x.get(sort_by, 0), reverse=(order=="desc"))
    return {"stats": stats, "total": 47, "page": page}

@app.get("/api/top-sectors")
def get_top_sectors(search: str = "", page: int = 1, limit: int = 10, session: Session = Depends(get_session)):
    q = select(MarketMetric.sector, func.count(MarketMetric.id).label("count")).group_by(MarketMetric.sector)
    if search:
        q = q.where(MarketMetric.sector.contains(search))
    total = len(session.exec(q).all())
    data = session.exec(q.order_by(func.count(MarketMetric.id).desc()).offset((page-1)*limit).limit(limit)).all()
    return {"sectors": [dict(r._mapping) for r in data], "total": total, "page": page}

@app.get("/api/opportunities")
def get_opportunities(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search:
        q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product:
        q = q.where(MarketMetric.product == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"opportunities": [m.dict() for m in data], "total": total, "page": page}

class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounty: str = ""
    budget_kes: float = 0
    business_model: str = "Retail"

# ========== 1. DATABASE MODELS ==========
class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"

    id: int | None = Field(default=None, primary_key=True)
    product: str | None = None
    county: str | None = None
    sector: str | None = None
    avg_price_kes: float | None = None
    demand_score: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"

    id: int | None = Field(default=None, primary_key=True)
    platform: str | None = None
    text: str | None = None
    county: str | None = None
    sector: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"

    id: int | None = Field(default=None, primary_key=True)
    title: str | None = None
    summary: str | None = None
    source: str | None = None
    category: str | None = None
    published_at: datetime = Field(default_factory=datetime.utcnow)

# ========== 2. REQUEST MODEL ==========
class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounty: str = ""
    budget_kes: float = 0
    business_model: str = "Retail"


@app.post("/analysis/detailed")
def detailed_analysis(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    try:
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)

        # ===== 1. MARKET PRICE ANALYSIS =====
        price_history_stmt = (
            select(MarketMetric)
           .where(MarketMetric.product.ilike(f"%{req.product}%"))
           .where(MarketMetric.county.ilike(f"%{req.county}%"))
           .where(MarketMetric.created_at >= last_30_days)
           .order_by(MarketMetric.created_at.asc())
        )
        price_history = session.exec(price_history_stmt).all()

        prices = [p.avg_price_kes for p in price_history if p.avg_price_kes]
        current_price = prices[-1] if prices else None
        avg_price_30d = statistics.mean(prices) if prices else None
        price_trend = "Stable"
        if len(prices) >= 2:
            price_trend = "Rising" if prices[-1] > prices[0] else "Falling"
        price_volatility = statistics.stdev(prices) if len(prices) > 1 else 0

        # ===== 2. DEMAND & SECTOR ANALYSIS =====
        demand_stmt = (
            select(MarketMetric)
           .where(MarketMetric.sector.ilike(f"%{req.sector}%"))
           .where(MarketMetric.county.ilike(f"%{req.county}%"))
           .where(MarketMetric.created_at >= last_30_days)
        )
        sector_data = session.exec(demand_stmt).all()
        demand_scores = [d.demand_score for d in sector_data if d.demand_score]
        avg_demand = statistics.mean(demand_scores) if demand_scores else 0
        demand_level = "Low" if avg_demand < 4 else "Medium" if avg_demand < 7 else "High"

        # Top products in sector
        products_in_sector = [d.product for d in sector_data if d.product]
        top_products = Counter(products_in_sector).most_common(3)

        # ===== 3. NEWS SENTIMENT & RISK =====
        news_stmt = (
            select(NewsArticle)
           .where(NewsArticle.category.ilike(f"%{req.sector}%"))
           .where(NewsArticle.published_at >= last_30_days)
           .order_by(NewsArticle.published_at.desc())
           .limit(10)
        )
        news = session.exec(news_stmt).all()

        risk_keywords = ["ban", "shortage", "tax", "drought", "protest", "inflation", "disease"]
        risk_news = [n for n in news if any(k in (n.title + n.summary).lower() for k in risk_keywords)]
        risk_score = min(10, len(risk_news) * 2) # 0-10

        # ===== 4. SOCIAL BUZZ ANALYSIS =====
        social_stmt = (
            select(SocialMention)
           .where(SocialMention.sector.ilike(f"%{req.sector}%"))
           .where(SocialMention.county.ilike(f"%{req.county}%"))
           .where(SocialMention.created_at >= last_7_days)
           .order_by(SocialMention.created_at.desc())
           .limit(20)
        )
        social = session.exec(social_stmt).all()
        platforms = Counter([s.platform for s in social if s.platform])

        # ===== 5. BUDGET FEASIBILITY =====
        units_possible = 0
        budget_rating = "N/A"
        if current_price and req.budget_kes > 0:
            units_possible = int(req.budget_kes / current_price)
            if units_possible > 100:
                budget_rating = "Excellent - Can buy in bulk"
            elif units_possible > 20:
                budget_rating = "Good - Can start small"
            else:
                budget_rating = "Tight - Consider smaller scale"

        # ===== 6. AI-STYLE RECOMMENDATION ENGINE =====
        score = 0
        reasons = []

        if avg_demand > 7:
            score += 3
            reasons.append(f"High demand in {req.county} for {req.sector}")
        if price_trend == "Rising":
            score += 2
            reasons.append("Prices are trending up - good margins")
        if risk_score < 4:
            score += 2
            reasons.append("Low risk news detected")
        if units_possible > 20:
            score += 2
            reasons.append("Budget is sufficient for market entry")
        if len(social) > 5:
            score += 1
            reasons.append("Active social buzz around sector")

        if score >= 8: recommendation = "STRONG BUY - Enter Market Now"
        elif score >= 5: recommendation = "CAUTIOUS BUY - Monitor and Enter"
        elif score >= 3: recommendation = "HOLD - Wait for better conditions"
        else: recommendation = "AVOID - High risk, Low demand"

        # ===== 7. FINAL EXTREMELY DETAILED REPORT =====
        return {
            "status": "success",
            "timestamp": now.isoformat(),
            "input_parameters": req.model_dump(),

            "market_summary": {
                "product": req.product,
                "sector": req.sector,
                "county": req.county,
                "subcounty": req.subcounty,
                "current_avg_price_kes": round(current_price, 2) if current_price else None,
                "30_day_avg_price_kes": round(avg_price_30d, 2) if avg_price_30d else None,
                "price_trend_30d": price_trend,
                "price_volatility": round(price_volatility, 2),
                "data_points": len(prices)
            },

            "demand_analysis": {
                "avg_demand_score_30d": round(avg_demand, 2),
                "demand_level": demand_level,
                "top_products_in_sector": [{"product": p[0], "mentions": p[1]} for p in top_products]
            },

            "risk_intelligence": {
                "risk_score_out_of_10": risk_score,
                "risk_level": "High" if risk_score > 6 else "Medium" if risk_score > 3 else "Low",
                "risk_headlines_found": len(risk_news),
                "recent_risks": [{"title": n.title, "date": n.published_at.isoformat()} for n in risk_news[:3]]
            },

            "social_intelligence": {
                "mentions_last_7_days": len(social),
                "platform_breakdown": dict(platforms),
                "sample_mentions": [{"platform": s.platform, "text": s.text[:100]} for s in social[:3]]
            },

            "budget_feasibility": {
                "budget_kes": req.budget_kes,
                "business_model": req.business_model,
                "estimated_units_you_can_buy": units_possible,
                "budget_rating": budget_rating
            },

            "final_verdict": {
                "overall_score_out_of_10": score,
                "recommendation": recommendation,
                "key_reasons": reasons,
                "next_steps": [
                    "Monitor prices weekly",
                    "Engage with local suppliers in " + req.county,
                    "Track news for " + req.sector + " sector"
                ] if score >= 5 else [
                    "Wait 2-4 weeks and re-check demand",
                    "Reduce initial budget risk",
                    "Look at alternative products"
                ]
            },

            "raw_data": {
                "news": [{"title": n.title, "source": n.source, "date": n.published_at.isoformat()} for n in news[:5]],
                "social": [{"platform": s.platform, "text": s.text[:150]} for s in social[:5]]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/export/{table}")
def export_csv(table: str, search: str = "", session: Session = Depends(get_session)):
    output = io.StringIO()
    writer = csv.writer(output)
    if table == "companies":
        q = select(KenyaLensBusiness)
        data = session.exec(q).all()
        writer.writerow(["Name","Sector","County","Rating","Reviews","Address","Lat","Lng"])
        [writer.writerow([r.name,r.sector,r.county,0,0,r.county,0,0]) for r in data]
    elif table == "prices":
        q = select(MarketMetric)
        data = session.exec(q).all()
        writer.writerow(["Product","Price","County","Market","Source","FetchedAt"])
        [writer.writerow([r.product,r.avg_price_kes,r.county,r.company_name,"KPIN",r.created_at]) for r in data]
    elif table == "demand":
        q = select(MarketMetric)
        data = session.exec(q).all()
        writer.writerow(["Product","Sector","County","DemandScore","MarketSizeKES","Growth%","Volume","OpportunityScore"])
        [writer.writerow([r.product,r.sector,r.county,r.demand_score,r.avg_price_kes,0,0,0]) for r in data]
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"})

@app.get("/api/social-feed")
def get_social_feed(platform: str = "all", session: Session = Depends(get_session)):
    q = select(SocialMention).order_by(SocialMention.created_at.desc()).limit(20)
    if platform!= "all":
        q = q.where(SocialMention.platform == platform)
    return {"posts": [p.dict() for p in session.exec(q).all()]}

@app.get("/api/news-feed")
def get_news_feed(session: Session = Depends(get_session)):
    return {"articles": [n.dict() for n in session.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(20)).all()]}

PRICING = {"BASIC": {"monthly": 500, "yearly": 5000}, "PROFESSIONAL": {"monthly": 1500, "yearly": 15000}, "ENTERPRISE": {"monthly": 5000, "yearly": 50000}}
ADDONS = {"EXTRA_REPORTS_10": {"name": "10 Extra Reports", "one_time": 1000}, "API_ACCESS": {"name": "API Access", "monthly": 2000}, "TEAM_SEAT": {"name": "Extra Team Seat", "monthly": 500}, "DATA_EXPORT": {"name": "Bulk Data Export", "one_time": 5000}}
ALC = {"CUSTOM_REPORT": {"name": "Custom Market Report", "price": 25000}, "DATA_ONBOARDING": {"name": "Data Onboarding", "price": 50000}, "TRAINING": {"name": "Team Training", "price": 15000}}

ALC = {...}

@app.get("/billing", response_class=HTMLResponse)
def billing(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("billing.html", {"request": request, "current_user": user, "plans": PRICING})

@app.get("/", response_class=HTMLResponse)
def home(request: Request, user: AuthUser = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "current_user": user,  # <-- THIS MAKES THE DROPDOWN WORK
        "data": data
    })

def get_mpesa_token():
    api_url = ("https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials")
    r = requests.get(api_url, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return r.json()["access_token"]

def get_timestamp():
    return datetime.now().strftime('%Y%m%d%H%M%S')

def get_password(shortcode, passkey, timestamp):
    return base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

@app.get("/api/pricing")
def api_pricing():
    return {"plans": PRICING, "addons": ADDONS, "alc": ALC}

@app.post("/api/checkout")
def mpesa_stk_push(payload: dict, user_id: int = Depends(get_current_user)):
    plan = payload.get("plan")
    billing = payload.get("billing")
    phone = payload.get("phone")
    amount = PRICING[billing]["monthly"]
    token = get_mpesa_token()
    timestamp = get_timestamp()
    password = get_password(MPESA_SHORTCODE, MPESA_PASSKEY, timestamp)
    api_url = ("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
    headers = {"Authorization": "Bearer " + token}
    payload_mpesa = {"BusinessShortCode": MPESA_SHORTCODE, "Password": password, "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": amount, "PartyA": phone, "PartyB": MPESA_SHORTCODE, "PhoneNumber": phone, "CallBackURL": MPESA_CALLBACK_URL, "AccountReference": f"EvidLens-{plan}-{user_id}", "TransactionDesc": f"{plan} {billing} Subscription"}
    r = requests.post(api_url, json=payload_mpesa, headers=headers)
    return r.json()

@app.post("/api/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        stk = data["Body"]["stkCallback"]
        if stk["ResultCode"] == 0:
            items = {i["Name"]: i["Value"] for i in stk["CallbackMetadata"]["Item"]}
            account_ref = items["AccountReference"]
            plan = account_ref.split("-")[1]
            user_id = int(account_ref.split("-")[2])
            expires = datetime.utcnow() + timedelta(days=30)
            sub = get_subscription(db, user_id)
            if sub:
                sub.plan = plan
                sub.status = "active"
                sub.expires_at = expires
            else:
                db.add(KenyaLensSubscription(user_id=user_id, plan=plan, status="active", expires_at=expires))
            db.commit()
    except Exception:
        pass
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.post("/api/run-scraper")
def run_scraper():
    scrape_kpin_prices()
    fetch_real_news()
    fetch_real_tweets()
    return {"status": "scraper ran. DB updated with real prices"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.5.12"}

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request, "plans": PRICING, "addons": ADDONS, "alc": ALC})

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})

import secrets
from datetime import timedelta

@app.post("/auth/forgot-password")
def forgot_password(req: dict, session: Session = Depends(get_session)):
    email = req["email"]
    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        return {"message": "If an account exists, a reset link has been sent"} # don't reveal if email exists

    # 1. Generate token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    session.add(user)
    session.commit()

    # 2. Send email - use Resend, Sendgrid, or Gmail SMTP
    reset_link = f"https://evidlens.co.ke/auth/reset-password?token={token}"
    send_email(
        to=email,
        subject="Reset your EvidLens password",
        body=f"Click here to reset: {reset_link}. Link expires in 1 hour."
    )

    return {"message": "Password reset link sent to your email"}

@app.get("/auth/reset-password")
def reset_page(request: Request, token: str, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.reset_token == token, User.reset_token_expires > datetime.utcnow())).first()
    if not user:
        return HTMLResponse("Link expired or invalid")
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})

@app.post("/auth/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.reset_token == token, User.reset_token_expires > datetime.utcnow())).first()
    if not user:
        return {"error": "Invalid token"}

    user.hashed_password = get_password_hash(password)
    user.reset_token = None
    user.reset_token_expires = None
    session.add(user)
    session.commit()
    return RedirectResponse("/login?success=Password reset", status_code=303)

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, session: Session = Depends(get_session)):
    data = dashboard_api(session)
    return templates.TemplateResponse("dashboard.html", {"request": request, "data": data, "API": os.getenv("API_BASE_URL"), "current_user": None})

@app.get("/competitive", response_class=HTMLResponse)
def competitive(request: Request, user: AuthUser = Depends(get_current_user), session: Session = Depends(get_session)):

    # Get user's last analysis to filter competitors
    last = session.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(1)).first()

    if last:
        stmt = select(Company).where(
            Company.sector == last.sector,
            Company.county == last.county
        ).limit(20)
        companies = session.exec(stmt).all()
        sector, county = last.sector, last.county
    else:
        companies = []
        sector, county = None, None

    return templates.TemplateResponse("competitive.html", {
        "request": request,
        "current_user": user,
        "companies": companies,
        "sector": sector,
        "county": county
    })

@app.get("/market/prices", response_class=HTMLResponse)
def prices_page(request: Request, session: Session = Depends(get_session)):
    prices = session.exec(select(MarketMetric).order_by(MarketMetric.created_at.desc()).limit(100)).all()
    return templates.TemplateResponse("prices.html", {"request": request, "prices": prices})

@app.get("/market/demand", response_class=HTMLResponse)
def demand_page(request: Request, session: Session = Depends(get_session)):
    demand = session.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
    return templates.TemplateResponse("demand.html", {"request": request, "demand": demand})

@app.get("/location/counties", response_class=HTMLResponse)
def counties_page(request: Request, session: Session = Depends(get_session)):
    counties = session.exec(select(func.distinct(MarketMetric.county))).all()
    stats = session.exec(select(MarketMetric.county, func.sum(MarketMetric.avg_price_kes).label("market_size")).group_by(MarketMetric.county)).all()
    return templates.TemplateResponse("counties.html", {"request": request, "counties": [c[0] for c in counties], "stats": [dict(s._mapping) for s in stats]})

@app.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request, session: Session = Depends(get_session)):
    posts = session.exec(select(SocialMention).order_by(SocialMention.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse("voice.html", {"request": request, "posts": posts})

@app.get("/kb/policy", response_class=HTMLResponse)
def policy_page(request: Request, session: Session = Depends(get_session)):
    policies = session.exec(select(NewsArticle).where(NewsArticle.category == "Policy").order_by(NewsArticle.published_at.desc()).limit(20)).all()
    return templates.TemplateResponse("policy.html", {"request": request, "policies": policies})

@app.get("/reports/funding", response_class=HTMLResponse)
def funding_page(request: Request, session: Session = Depends(get_session)):
    funders = session.exec(select(KenyaLensBusiness).where(or_(KenyaLensBusiness.sector.ilike("%Financial%"),KenyaLensBusiness.sector.ilike("%Banking%"),KenyaLensBusiness.sector.ilike("%Insurance%"),KenyaLensBusiness.sector.ilike("%SACCO%"))).limit(50)).all()
    return templates.TemplateResponse("funding.html", {"request": request, "funders": funders})

@app.get("/kenyalensiq")
def kenyalsiq_dashboard(session: Session = Depends(get_session)):
    business_count = session.exec(select(func.count(KenyaLensBusiness.id))).one()
    survey_count = session.exec(select(func.count(KenyaLensSurvey.id))).one()
    response_count = session.exec(select(func.count(KenyaLensResponse.id))).one()
    tenant_count = session.exec(select(func.count(KenyaTenant.id))).one()
    user_count = session.exec(select(func.count(KenyaLensMember.id))).one()

    return {"title": "KenyaLensIQ", "modules": [{"id": 1, "name": "Businesses", "icon": "🏢", "count": business_count, "route": "/businesses"}, {"id": 2, "name": "Surveys", "icon": "📋", "count": survey_count, "route": "/surveys"}, {"id": 3, "name": "Responses", "icon": "📝", "count": response_count, "route": "/responses"}, {"id": 4, "name": "Tenants", "icon": "🏛️", "count": tenant_count, "route": "/tenants"}, {"id": 5, "name": "Users", "icon": "👥", "count": user_count, "route": "/users"}]}

@app.get("/dashboard")
async def dashboard(request: Request, current_user: AuthUser = Depends(get_current_user)):
    session = Session(engine)
    data = dashboard_api(session)
    session.close()
    
    API = {
        "logout": "/auth/logout",
        "login": "/login",
        "prices": "/api/prices",
        "demand": "/api/demand",
        "companies": "/api/companies",
        "county_stats": "/api/county-stats",
        "sectors": "/api/top-sectors",
        "opportunities": "/api/opportunities",
        "get_sectors": "/api/sectors",
        "get_counties": "/api/counties",
        "get_subcounties": "/api/subcounties",
        "analyze": "/api/analyze-detailed",
        "chat": "/lens/chat",
        "download": "/download-report",
        "export": "/api/export",
        "money_embed": "/kenyalensiq/embed/money"
    }
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "current_user": current_user, "data": data, "API": API})

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("settings.html", {"request": request, "current_user": user})

@app.get("/billing", response_class=HTMLResponse)
def billing(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("billing.html", {"request": request, "current_user": user, "plans": PRICING})

@app.get("/security", response_class=HTMLResponse)
def security(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("security.html", {"request": request, "current_user": user})

@app.get("/history", response_class=HTMLResponse)
def history(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("history.html", {"request": request, "current_user": user})

@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("stats.html", {"request": request, "current_user": user})

@app.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("wallet.html", {"request": request, "current_user": user})

@app.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request, user: AuthUser = Depends(get_current_user)): 
    return templates.TemplateResponse("workspaces.html", {"request": request, "current_user": user})

@app.get("/help", response_class=HTMLResponse)
def help(request: Request): 
    return templates.TemplateResponse("help.html", {"request": request})

@app.get("/changelog", response_class=HTMLResponse)
def changelog(request: Request): 
    return templates.TemplateResponse("changelog.html", {"request": request})

@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request): 
    return templates.TemplateResponse("forgot.html", {"request": request})

@app.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, token: str): 
    return templates.TemplateResponse("reset.html", {"request": request, "token": token})

    @app.get("/history", response_class=HTMLResponse)
def history(request: Request, session: Session = Depends(get_session), user: AuthUser = Depends(get_current_user)):
    stmt = select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(50)
    analyses = session.exec(stmt).all()
    return templates.TemplateResponse("history.html", {"request": request, "current_user": user, "analyses": analyses})

@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request, session: Session = Depends(get_session), user: AuthUser = Depends(get_current_user)):
    total = session.exec(select(func.count()).where(MarketMetric.user_id == user.id)).first()

    # Top counties
    county_stmt = select(MarketMetric.county, func.count().label("c")).where(MarketMetric.user_id == user.id).group_by(MarketMetric.county).order_by(desc("c")).limit(5)
    top_counties = session.exec(county_stmt).all()

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "current_user": user,
        "total_analyses": total,
        "credits_spent": total, # 1 credit per analysis
        "top_counties": top_counties
    })

@app.get("/kenyalensiq/embed/money")
def money_module_embed(query: str = "", session: Session = Depends(get_session)):
    funding_count = session.exec(select(func.count(KenyaLensBusiness.id)).where(or_(KenyaLensBusiness.sector.ilike("%Financial%"),KenyaLensBusiness.sector.ilike("%Banking%"),KenyaLensBusiness.sector.ilike("%Insurance%"),KenyaLensBusiness.sector.ilike("%SACCO%"),KenyaLensBusiness.sector.ilike("%Microfinance%"),KenyaLensBusiness.sector.ilike("%FinTech%")))).one()
    sector_breakdown = session.exec(select(KenyaLensBusiness.sector, func.count(KenyaLensBusiness.id).label("count")).where(or_(KenyaLensBusiness.sector.ilike("%Financial%"),KenyaLensBusiness.sector.ilike("%Banking%"),KenyaLensBusiness.sector.ilike("%Insurance%"),KenyaLensBusiness.sector.ilike("%SACCO%"),KenyaLensBusiness.sector.ilike("%Microfinance%"),KenyaLensBusiness.sector.ilike("%FinTech%"))).group_by(KenyaLensBusiness.sector)).all()
    if query:
        sector_breakdown = [r for r in sector_breakdown if query.lower() in r.sector.lower()]
    return {"module": "Money Module - Sector Breakdown", "total_funding_businesses": funding_count, "query": query, "data": [dict(r._mapping) for r in sector_breakdown]}

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

# ========== 2. DATABASE MODELS ==========
class MarketMetric(SQLModel, table=True):
    __tablename__ = "market_metrics"
    id: Optional[int] = Field(default=None, primary_key=True)
    product: Optional[str] = None
    county: Optional[str] = None
    subcounty: Optional[str] = None
    sector: Optional[str] = None
    avg_price_kes: Optional[float] = None
    demand_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: Optional[str] = None
    text: Optional[str] = None
    county: Optional[str] = None
    subcounty: Optional[str] = None
    sector: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class NewsArticle(SQLModel, table=True):
    __tablename__ = "news_articles"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    county: Optional[str] = None
    published_at: datetime = Field(default_factory=datetime.utcnow)

class GeoData(SQLModel, table=True):
    __tablename__ = "geo_data"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    type: str = Field(index=True, max_length=20)
    parent: Optional[str] = Field(default=None, index=True, max_length=100)

class SectorReport(SQLModel, table=True):
    __tablename__ = "sector_reports"
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True, max_length=100)
    county: Optional[str] = Field(default=None, index=True, max_length=50)
    title: str = Field(max_length=255)
    summary: str
    key_insights: List[dict] = Field(default=[], sa_column=Column(JSON))
    market_size_kes: Optional[float] = Field(default=None)
    growth_rate_percent: Optional[float] = Field(default=None)
    top_challenges: List[dict] = Field(default=[], sa_column=Column(JSON))
    opportunities: List[dict] = Field(default=[], sa_column=Column(JSON))
    data_sources: List[dict] = Field(default=[], sa_column=Column(JSON))
    generated_by: str = Field(default="EvidLens AI RAG", max_length=100)
    version: str = Field(default="v1.0", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

# ========== 3. REQUEST MODEL ==========
class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounties: List[str] = Field(default=["All"])
    budget_kes: float = 0
    business_model: str = "Retail"

    @field_validator('product', 'sector', 'county')
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    class Config:
        extra = "allow"

# ========== 4. ROUTER ==========
router = APIRouter()

@router.get("/meta/sectors")
def get_sectors(db: Session = Depends(get_session)):
    stmt = select(SectorReport.sector).distinct().order_by(SectorReport.sector)
    sectors = db.exec(stmt).all()
    return {"sectors": sectors or KENYA_SECTORS}

@router.get("/meta/counties")
def get_counties(db: Session = Depends(get_session)):
    stmt = select(GeoData.name).where(GeoData.type == "county").order_by(GeoData.name)
    counties = db.exec(stmt).all()
    return {"counties": counties or KENYA_COUNTIES}

@router.get("/meta/subcounties")
def get_subcounties(county: str, db: Session = Depends(get_session)):
    stmt = select(GeoData.name).where(
        GeoData.type == "subcounty",
        sqlfunc.lower(GeoData.parent) == county.lower()
    ).order_by(GeoData.name)
    subcounties = db.exec(stmt).all()
    return {"subcounties": ["All"] + subcounties}

@router.post("/analysis/detailed")
def detailed_analysis(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    try:
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)
        last_7_days = now - timedelta(days=7)

        county_filter = MarketMetric.county.ilike(f"%{req.county}%")
        subcounty_filter = True
        if "All" not in req.subcounties:
            subcounty_filter = MarketMetric.subcounty.in_(req.subcounties)

        # ===== 1. PRICE + TREND + FORECAST =====
        price_history_stmt = select(MarketMetric).where(
            MarketMetric.product.ilike(f"%{req.product}%"),
            county_filter, subcounty_filter,
            MarketMetric.created_at >= last_90_days
        ).order_by(MarketMetric.created_at.asc())
        price_history = session.exec(price_history_stmt).all()
        prices = [p.avg_price_kes for p in price_history if p.avg_price_kes]

        current_price = prices[-1] if prices else None
        avg_price_30d = statistics.mean(prices[-30:]) if len(prices) >= 30 else statistics.mean(prices) if prices else None
        price_trend = "Stable"
        if len(prices) >= 2:
            price_trend = "Rising" if prices[-1] > prices[0] * 1.05 else "Falling" if prices[-1] < prices[0] * 0.95 else "Stable"
        price_volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        forecast_90d = round(current_price * 1.03, 2) if price_trend == "Rising" and current_price else current_price

        # ===== 2. DEMAND + SEASONALITY =====
        demand_stmt = select(MarketMetric).where(
            MarketMetric.sector.ilike(f"%{req.sector}%"),
            county_filter, subcounty_filter,
            MarketMetric.created_at >= last_30_days
        )
        sector_data = session.exec(demand_stmt).all()
        demand_scores = [d.demand_score for d in sector_data if d.demand_score]
        avg_demand = statistics.mean(demand_scores) if demand_scores else 0
        demand_level = "Low" if avg_demand < 4 else "Medium" if avg_demand < 7 else "High"
        products_in_sector = [d.product for d in sector_data if d.product]
        top_products = Counter(products_in_sector).most_common(5)

        seasonal_stmt = select(MarketMetric).where(
            MarketMetric.product.ilike(f"%{req.product}%"),
            county_filter
        ).order_by(MarketMetric.created_at.desc()).limit(12)
        seasonal_data = session.exec(seasonal_stmt).all()
        seasonality = "Peak Season" if len(seasonal_data) > 6 and statistics.mean([d.demand_score or 0 for d in seasonal_data[:3]]) > statistics.mean([d.demand_score or 0 for d in seasonal_data[-3:]]) else "Off Season"

        # ===== 3. COMPETITORS =====
        competitor_stmt = select(MarketMetric.product).where(
            MarketMetric.sector.ilike(f"%{req.sector}%"),
            county_filter
        ).distinct().limit(10)
        competitors = session.exec(competitor_stmt).all()
        top_competitors = [c for c in competitors if c and req.product.lower() not in c.lower()][:5]

        # ===== 4. SUPPLY CHAIN + DISTRIBUTION =====
        supply_risk_keywords = ["shortage", "transport", "drought", "flood", "strike"]
        supply_news = [n for n in session.exec(select(NewsArticle).where(
            NewsArticle.county.ilike(f"%{req.county}%"),
            NewsArticle.published_at >= last_30_days
        )).all() if any(k in ((n.title or "") + (n.summary or "")).lower() for k in supply_risk_keywords)]
        supply_chain_risk = "High" if len(supply_news) > 3 else "Medium" if len(supply_news) > 0 else "Low"

        distribution_channels = []
        if req.business_model == "Retail": distribution_channels = ["Dukas", "Supermarkets", "Open Markets"]
        elif req.business_model == "Wholesale": distribution_channels = ["Distributors", "Bulk Buyers", "Institutions"]
        else: distribution_channels = ["E-commerce", "Direct to Consumer"]

        # ===== 5. PROFIT MARGIN ESTIMATE =====
        estimated_cost_price = current_price * 0.75 if current_price else None
        estimated_margin_percent = 25.0
        estimated_profit_per_unit = current_price - estimated_cost_price if current_price and estimated_cost_price else None

        # ===== 6. RISK INTELLIGENCE =====
        news_stmt = select(NewsArticle).where(
            NewsArticle.category.ilike(f"%{req.sector}%"),
            NewsArticle.county.ilike(f"%{req.county}%"),
            NewsArticle.published_at >= last_30_days
        ).order_by(NewsArticle.published_at.desc()).limit(10)
        news = session.exec(news_stmt).all()
        risk_keywords = ["ban", "shortage", "tax", "drought", "protest", "inflation", "disease", "policy"]
        risk_news = [n for n in news if any(k in ((n.title or "") + (n.summary or "")).lower() for k in risk_keywords)]
        risk_score = min(10, len(risk_news) * 2)

        # ===== 7. SOCIAL BUZZ =====
        social_stmt = select(SocialMention).where(
            SocialMention.sector.ilike(f"%{req.sector}%"),
            SocialMention.county.ilike(f"%{req.county}%"),
            subcounty_filter if subcounty_filter!= True else True,
            SocialMention.created_at >= last_7_days
        ).order_by(SocialMention.created_at.desc()).limit(20)
        social = session.exec(social_stmt).all()
        platforms = Counter([s.platform for s in social if s.platform])
        sentiment_score = 6.5

        # ===== 8. BUDGET FEASIBILITY =====
        units_possible = int(req.budget_kes / current_price) if current_price and req.budget_kes > 0 else 0
        estimated_revenue = units_possible * current_price if current_price else 0
        estimated_profit = units_possible * estimated_profit_per_unit if estimated_profit_per_unit else 0
        roi_percent = (estimated_profit / req.budget_kes * 100) if req.budget_kes > 0 else 0

        # ===== 9. SCORING ENGINE =====
        score = 0
        reasons = []
        if avg_demand > 7: score += 3; reasons.append(f"High demand in {req.county}")
        if price_trend == "Rising": score += 2; reasons.append("Prices trending up")
        if risk_score < 4: score += 2; reasons.append("Low regulatory risk")
        if units_possible > 20: score += 2; reasons.append("Budget sufficient for scale")
        if supply_chain_risk == "Low": score += 1; reasons.append("Stable supply chain")
        if seasonality == "Peak Season": score += 1; reasons.append("Currently peak season")

        if score >= 9: recommendation = "STRONG BUY - Enter Market Now"
        elif score >= 6: recommendation = "BUY - Good Opportunity"
        elif score >= 4: recommendation = "HOLD - Monitor 30 days"
        else: recommendation = "AVOID - High risk"

        # ===== FINAL PAYLOAD =====
        return {
            "status": "success",
            "timestamp": now.isoformat(),
            "input_parameters": req.model_dump(),
            "market_overview": {
                "product": req.product,
                "sector": req.sector,
                "location": {"county": req.county, "subcounties": req.subcounties},
                "current_price_kes": round(current_price, 2) if current_price else None,
                "30_day_avg_kes": round(avg_price_30d, 2) if avg_price_30d else None,
                "90_day_forecast_kes": forecast_90d,
                "price_trend": price_trend,
                "volatility": round(price_volatility, 2),
                "seasonality": seasonality
            },
            "demand_competition": {
                "demand_level": demand_level,
                "avg_demand_score": round(avg_demand, 2),
                "top_products_in_sector": [{"product": p[0], "count": p[1]} for p in top_products],
                "top_competitors": top_competitors
            },
            "financials": {
                "budget_kes": req.budget_kes,
                "business_model": req.business_model,
                "estimated_cost_per_unit": round(estimated_cost_price, 2) if estimated_cost_price else None,
                "estimated_margin_percent": estimated_margin_percent,
                "estimated_profit_per_unit": round(estimated_profit_per_unit, 2) if estimated_profit_per_unit else None,
                "units_you_can_buy": units_possible,
                "estimated_monthly_revenue": round(estimated_revenue, 2),
                "estimated_monthly_profit": round(estimated_profit, 2),
                "estimated_roi_percent": round(roi_percent, 2)
            },
            "operations": {
                "recommended_distribution": distribution_channels,
                "supply_chain_risk": supply_chain_risk,
                "supply_risk_events": len(supply_news)
            },
            "risk_intelligence": {
                "risk_score_10": risk_score,
                "risk_level": "High" if risk_score > 6 else "Medium" if risk_score > 3 else "Low",
                "recent_risks": [{"title": n.title, "date": n.published_at.isoformat()} for n in risk_news[:3]]
            },
            "social_intelligence": {
                "mentions_7d": len(social),
                "platforms": dict(platforms),
                "sentiment_score_10": sentiment_score
            },
            "final_verdict": {
                "overall_score_10": score,
                "recommendation": recommendation,
                "key_reasons": reasons,
                "next_steps": [
                    f"Source suppliers in {req.county}",
                    "Lock pricing for 30 days if trend is rising",
                    "Monitor news for policy changes"
                ] if score >= 6 else [
                    "Wait and re-evaluate in 30 days",
                    "Test with smaller budget",
                    "Look at alternative products"
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

app.include_router(router)

# ========== 5. SEED FUNCTION ==========
def seed_geo_data(db: Session):
    for c in KENYA_COUNTIES:
        if not db.exec(select(GeoData).where(GeoData.name==c, GeoData.type=="county")).first():
            db.add(GeoData(name=c, type="county", parent="Kenya"))
    for county, subcounties in KENYA_SUBCOUNTIES.items():
        for sc in subcounties:
            if not db.exec(select(GeoData).where(GeoData.name==sc, GeoData.type=="subcounty")).first():
                db.add(GeoData(name=sc, type="subcounty", parent=county))
    if not db.exec(select(SectorReport)).first():
        for s in KENYA_SECTORS:
            db.add(SectorReport(sector=s, title=f"{s} Report", summary="Seeded"))
    db.commit()

NAVY = colors.HexColor("#0B1D3A")
TEAL = colors.HexColor("#009688")
LIGHT_TEAL = colors.HexColor("#E0F2F1")
GREEN = colors.HexColor("#10B981")
YELLOW = colors.HexColor("#F59E0B")
RED = colors.HexColor("#EF4444")

def create_chart(fig_func):
    buf = BytesIO()
    fig_func()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', transparent=True)
    plt.close()
    buf.seek(0)
    return Image(buf, width=80*mm, height=50*mm)

def donut_chart(data, labels, title):
    def _plot():
        fig, ax = plt.subplots(figsize=(3,3))
        ax.pie(data, labels=labels, autopct='%1.0f%%', startangle=90,
               wedgeprops=dict(width=0.4), colors=['#009688','#26A69A','#4DB6AC','#80CBC4','#B2DFDB'])
        ax.set_title(title, fontsize=10, color="#0B1D3A", fontweight='bold')
    return create_chart(_plot)

def bar_chart(data, labels, title):
    def _plot():
        fig, ax = plt.subplots(figsize=(4,3))
        ax.barh(labels, data, color='#009688')
        ax.set_title(title, fontsize=10, color="#0B1D3A", fontweight='bold')
        ax.invert_yaxis()
        for i, v in enumerate(data): ax.text(v, i, f" {v}", va='center', fontsize=8)
        plt.tight_layout()
    return create_chart(_plot)

@app.post("/analysis/download-pdf")
def download_pdf(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    analysis_data = detailed_analysis(req, session)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleNavy', fontSize=20, textColor=NAVY, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='SubtitleTeal', fontSize=12, textColor=TEAL, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='Sidebar', fontSize=9, textColor=colors.white, leading=12))
    styles.add(ParagraphStyle(name='KPIBig', fontSize=22, textColor=NAVY, fontName="Helvetica-Bold", alignment=1))
    styles.add(ParagraphStyle(name='KPISmall', fontSize=9, textColor=NAVY, alignment=1))
    styles.add(ParagraphStyle(name='Insight', fontSize=9, backColor=LIGHT_TEAL, borderPadding=4))

    story = []
    mo = analysis_data['market_overview']
    fin = analysis_data['financials']
    fv = analysis_data['final_verdict']
    dc = analysis_data['demand_competition']
    ri = analysis_data['risk_intelligence']
    ops = analysis_data['operations']
    soc = analysis_data['social_intelligence']

    logo_path = os.path.join(os.getcwd(), "app", "static", "logo.png")
    icon_path = lambda name: os.path.join(os.getcwd(), "app", "static", "icons", f"{name}.png")

    # ===== PAGE 1: EXECUTIVE SUMMARY =====
    # LEFT SIDEBAR
    sidebar_elements = []
    if os.path.exists(logo_path): sidebar_elements.append(Image(logo_path, width=22*mm, height=22*mm))
    sidebar_elements.append(Paragraph("EvidLens<br/>Research & Consulting", styles['Sidebar']))
    sidebar_elements.append(Spacer(1, 8))
    sidebar_elements.append(Paragraph("<font color='#26A69A'>REPORT OVERVIEW</font>", styles['Sidebar']))

    for icon, label, value in [
        ("date", "DATE", datetime.utcnow().strftime("%B %Y")),
        ("location", "COVERAGE", f"{req.county} County"),
        ("sector", "SECTOR", req.sector),
        ("budget", "BUDGET", f"KES {fin['budget_kes']:,}")
    ]:
        row = [Image(icon_path(icon), 4*mm, 4*mm)] if os.path.exists(icon_path(icon)) else []
        row.append(Paragraph(f"<b>{label}</b><br/>{value}", styles['Sidebar']))
        sidebar_elements.append(Table([row], colWidths=[6*mm, 44*mm]))

    sidebar_table = Table([[el] for el in sidebar_elements], colWidths=[50*mm])
    sidebar_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), NAVY), ('PADDING', (0,0), (-1,-1), 6)]))

    # RIGHT CONTENT
    main_elements = []
    main_elements.append(Paragraph("ANALYTICAL FINDINGS", styles['TitleNavy']))
    main_elements.append(Paragraph(f"MARKET REPORT - {req.product.upper()} IN {req.county.upper()}", styles['SubtitleTeal']))
    main_elements.append(Spacer(1, 6))

    # KPI ROW
    kpi_data = [
        [Paragraph(f"KES {mo['current_price_kes'] or 'N/A'}", styles['KPIBig']),
         Paragraph(f"{dc['demand_level']}", styles['KPIBig']),
         Paragraph(f"{fv['overall_score_10']}/10", styles['KPIBig'])],
        [Paragraph("Current Price", styles['KPISmall']),
         Paragraph("Demand Level", styles['KPISmall']),
         Paragraph("Overall Score", styles['KPISmall'])]
    ]
    kpi_table = Table(kpi_data, colWidths=[40*mm, 40*mm, 40*mm])
    kpi_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, LIGHT_TEAL), ('BACKGROUND', (0,0), (-1,-1), LIGHT_TEAL)]))
    main_elements.append(kpi_table)
    main_elements.append(Spacer(1, 8))

    # RECOMMENDATION
    rec_color = GREEN if fv['overall_score_10'] >= 7 else YELLOW if fv['overall_score_10'] >= 4 else RED
    rec_table = Table([[Paragraph(f"<b>{fv['recommendation']}</b>", styles['Normal'])]], colWidths=[120*mm])
    rec_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), rec_color), ('TEXTCOLOR', (0,0), (-1,-1), colors.white), ('PADDING', (0,0), (-1,-1), 8)]))
    main_elements.append(rec_table)
    for reason in fv['key_reasons']:
        main_elements.append(Paragraph(f"• {reason}", styles['Normal']))
    main_elements.append(Spacer(1, 8))

    # CHARTS ROW
    price_data = [mo['current_price_kes'] or 0, mo['30_day_avg_kes'] or 0, mo['90_day_forecast_kes'] or 0]
    price_labels = ['Current', '30D Avg', '90D Forecast']
    donut = donut_chart(price_data, price_labels, "Price Trend")

    comp_data = [p['count'] for p in dc['top_products_in_sector'][:5]]
    comp_labels = [p['product'][:15] for p in dc['top_products_in_sector'][:5]]
    bar = bar_chart(comp_data, comp_labels, "Top Products in Sector")

    charts_table = Table([[donut, bar]], colWidths=[85*mm, 85*mm])
    main_elements.append(charts_table)
    main_elements.append(Spacer(1, 8))

    # INSIGHT BOX
    main_elements.append(Paragraph(f"<b>Insight:</b> {mo['price_trend']} trend with {mo['seasonality']}. Risk level is {ri['risk_level']}.", styles['Insight']))

    # COMBINE PAGE 1
    page1 = Table([[sidebar_table, main_elements]], colWidths=[55*mm, 125*mm])
    page1.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(page1)
    story.append(PageBreak())

    # ===== PAGE 2: DETAILS =====
    story.append(Paragraph("DETAILED ANALYSIS", styles['TitleNavy']))
    story.append(Spacer(1, 6))

    # FINANCIALS
    story.append(Paragraph("1. FINANCIALS & FEASIBILITY", styles['SubtitleTeal']))
    fin_data = [["Metric", "Value"],
        ["Budget KES", f"{fin['budget_kes']:,}"],
        ["Business Model", fin['business_model']],
        ["Units You Can Buy", fin['units_you_can_buy']],
        ["Est. Cost Per Unit", f"KES {fin['estimated_cost_per_unit']}"],
        ["Est. Monthly Profit", f"KES {fin['estimated_monthly_profit']:,}"],
        ["Est. ROI", f"{fin['estimated_roi_percent']}%"]]
    fin_table = Table(fin_data, colWidths=[90*mm, 90*mm])
    fin_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), NAVY), ('TEXTCOLOR', (0,0), (-1,0), colors.white)]))
    story.append(fin_table)
    story.append(Spacer(1, 8))

    # DEMAND + COMPETITION
    story.append(Paragraph("2. DEMAND & COMPETITION", styles['SubtitleTeal']))
    story.append(Paragraph(f"<b>Demand Score:</b> {dc['avg_demand_score']}/10 - {dc['demand_level']}", styles['Normal']))
    story.append(Paragraph(f"<b>Top Competitors:</b> {', '.join(dc['top_competitors']) or 'None'}", styles['Normal']))
    story.append(Spacer(1, 8))

    # OPERATIONS + RISK
    story.append(Paragraph("3. OPERATIONS & RISK", styles['SubtitleTeal']))
    story.append(Paragraph(f"<b>Distribution:</b> {', '.join(ops['recommended_distribution'])}", styles['Normal']))
    story.append(Paragraph(f"<b>Supply Chain Risk:</b> {ops['supply_chain_risk']} - {ops['supply_risk_events']} events", styles['Normal']))
    story.append(Paragraph(f"<b>Risk Score:</b> {ri['risk_score_10']}/10 - {ri['risk_level']}", styles['Normal']))
    story.append(Spacer(1, 8))

    # SOCIAL
    story.append(Paragraph("4. SOCIAL INTELLIGENCE - 7 DAYS", styles['SubtitleTeal']))
    story.append(Paragraph(f"Mentions: {soc['mentions_7d']} | Sentiment: {soc['sentiment_score_10']}/10", styles['Normal']))
    story.append(Paragraph(f"Platforms: {', '.join(soc['platforms'].keys())}", styles['Normal']))
    story.append(Spacer(1, 8))

    # NEXT STEPS
    story.append(Paragraph("5. RECOMMENDATIONS & NEXT STEPS", styles['SubtitleTeal']))
    for i, step in enumerate(fv['next_steps'], 1):
        story.append(Paragraph(f"{i}. {step}", styles['Normal']))

    story.append(Spacer(1, 15))
    story.append(Paragraph("Powered by EvidLens AI RAG | Data is indicative and for decision support only.", styles['Italic']))

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=EvidLens_Report_{req.product}_{req.county}.pdf"})

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
def catch_all(path: str):
    return {"status": "ok"}

@app.get("/analysis/trending")
def get_trending(session: Session = Depends(get_session)):
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    
    stmt = select(
        MarketMetric.product,
        MarketMetric.county,
        MarketMetric.sector,
        func.avg(MarketMetric.demand_score).label("avg_demand"),
        func.avg(MarketMetric.current_price_kes).label("avg_price"),
        func.count(MarketMetric.id).label("activity_count")
    ).where(MarketMetric.timestamp > two_weeks_ago) \
     .group_by(MarketMetric.product, MarketMetric.county, MarketMetric.sector) \
     .order_by(desc("activity_count")).limit(6)
    
    results = session.exec(stmt).all()
    
    trending_list = []
    for r in results:
        old_stmt = select(func.avg(MarketMetric.current_price_kes)).where(
            MarketMetric.product == r.product,
            MarketMetric.county == r.county,
            MarketMetric.timestamp.between(two_weeks_ago - timedelta(days=30), two_weeks_ago)
        )
        old_avg = session.exec(old_stmt).first() or r.avg_price
        
        price_change = 0
        if old_avg and old_avg > 0:
            price_change = round(((r.avg_price - old_avg) / old_avg) * 100, 1)
        
        trend = "up" if price_change > 0 else "down" if price_change < 0 else "stable"
        
        trending_list.append({
            "product": r.product,
            "county": r.county,
            "sector": r.sector,
            "demand_score": round(r.avg_demand or 0, 1),
            "current_price_kes": int(r.avg_price or 0),
            "price_change_percent": price_change,
            "trend": trend,
            "activity": r.activity_count
        })
    
    return {"trending": trending_list}

@app.get("/analysis/search")
def search_insights(
    q: str = "", 
    county: str = None,
    sector: str = None, 
    min_demand: float = 0,
    session: Session = Depends(get_session)
):
    if not q and not county and not sector:
        return {"results": [], "total": 0}

    # Base query
    stmt = select(MarketMetric)
    
    filters = []
    
    # 1. Full-text search across multiple fields
    if q:
        search_term = f"%{q}%"
        filters.append(
            or_(
                MarketMetric.product.ilike(search_term),
                MarketMetric.county.ilike(search_term),
                MarketMetric.sector.ilike(search_term),
                MarketMetric.notes.ilike(search_term) # if you have notes/insights field
            )
        )
    
    # 2. Filters
    if county:
        filters.append(MarketMetric.county == county)
    if sector:
        filters.append(MarketMetric.sector == sector)
    if min_demand > 0:
        filters.append(MarketMetric.demand_score >= min_demand)
    
    if filters:
        stmt = stmt.where(*filters)
    
    # 3. Smart ranking: demand_score * 0.5 + recency * 0.3 + activity * 0.2
    days_old = func.julianday('now') - func.julianday(MarketMetric.timestamp)
    recency_score = func.max(0, 30 - days_old) # newer = higher
    relevance = (MarketMetric.demand_score * 0.5) + (recency_score * 0.3) + (MarketMetric.activity_count * 0.2)
    
    stmt = stmt.order_by(desc(relevance)).limit(50)
    
    results = session.exec(stmt).all()
    
    # 4. Return rich data for frontend cards
    formatted = []
    for r in results:
        formatted.append({
            "id": r.id,
            "product": r.product,
            "county": r.county,
            "sector": r.sector,
            "current_price_kes": r.current_price_kes,
            "demand_score": r.demand_score,
            "risk_level": r.risk_level,
            "recommendation": r.recommendation,
            "timestamp": r.timestamp,
            "snippet": f"{r.product} in {r.county} - Demand {r.demand_score}/10. {r.recommendation}"
        })
    
    return {"results": formatted, "total": len(formatted)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
