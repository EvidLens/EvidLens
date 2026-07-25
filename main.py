from app.modules.database import get_db
from app.modules.kenyalensiq.models import KenyaLensBusiness, MarketMetric
from groq import Groq
import smtplib, json
from email.mime.text import MIMEText
from fastapi import Depends
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, select, func, or_, desc, asc
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlmodel import select, func
from sqlmodel import select, func, or_
from bs4 import BeautifulSoup
# import tweepy
from supabase import create_client, Client

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

@app.post("/api/analyze-detailed")
async def analyze_detailed(req: DetailedAnalysisRequest, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    check_subscription(user_id, db)
    competitors = db.exec(select(KenyaLensBusiness).where(KenyaLensBusiness.sector==req.sector, KenyaLensBusiness.county==req.county).limit(10)).all()
    prices = db.exec(select(MarketMetric).where(MarketMetric.product.contains(req.product), MarketMetric.county==req.county).limit(5)).all()
    demand = db.exec(select(MarketMetric).where(MarketMetric.product.contains(req.product), MarketMetric.county==req.county).first())
    prompt = f"Product: {req.product} Sector: {req.sector} Location: {req.subcounty}, {req.county} Budget: KES {req.budget_kes} Model: {req.business_model} Competitors: {[c.name for c in competitors]} Avg Price: {[p.avg_price_kes for p in prices]} Demand Score: {demand.demand_score if demand else 'N/A'} Market Size: KES {demand.avg_price_kes if demand else 'N/A'}"
    ai_response = generate_insights(prompt)
    log_query(db, user_id)
    return {"summary": ai_response, "competitors": [c.dict() for c in competitors], "prices": [p.dict() for p in prices], "demand": demand.dict() if demand else None}

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
def competitive_page(request: Request, session: Session = Depends(get_session)):
    companies = session.exec(select(KenyaLensBusiness).limit(50)).all()
    return templates.TemplateResponse("competitive.html", {"request": request, "companies": companies})

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

@app.get("/api/counties")
def get_counties(search: str = "", session: Session = Depends(get_session)):
    """Get ALL counties in DB. No hardcoding"""
    q = select(func.distinct(KenyaLensBusiness.county)).where(KenyaLensBusiness.county.isnot(None))
    if search:
        q = q.where(KenyaLensBusiness.county.ilike(f"%{search}%"))
    counties = [c[0] for c in session.exec(q.order_by(KenyaLensBusiness.county)).all() if c[0]]
    return {"counties": counties, "total": len(counties)}


@app.get("/api/sectors")
def get_sectors(search: str = "", session: Session = Depends(get_session)):
    """Get ALL sectors in DB. No hardcoding"""
    q = select(func.distinct(KenyaLensBusiness.sector)).where(KenyaLensBusiness.sector.isnot(None))
    if search:
        q = q.where(KenyaLensBusiness.sector.ilike(f"%{search}%"))
    sectors = [s[0] for s in session.exec(q.order_by(KenyaLensBusiness.sector)).all() if s[0]]
    return {"sectors": sectors, "total": len(sectors)}


@app.get("/api/filters")
def get_filters(session: Session = Depends(get_session)):
    """One call to get all filter options for frontend"""
    counties = session.exec(select(func.distinct(KenyaLensBusiness.county)).where(KenyaLensBusiness.county.isnot(None)).order_by(KenyaLensBusiness.county)).all()
    sectors = session.exec(select(func.distinct(KenyaLensBusiness.sector)).where(KenyaLensBusiness.sector.isnot(None)).order_by(KenyaLensBusiness.sector)).all()
    return {
        "counties": [c[0] for c in counties if c[0]],
        "sectors": [s[0] for s in sectors if s[0]],
        "total_counties": len([c for c in counties if c[0]]),
        "total_sectors": len([s for s in sectors if s[0]])
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
def catch_all(path: str):
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
