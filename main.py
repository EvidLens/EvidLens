from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import Session, select, func, or_, desc, asc
from pydantic import BaseModel
from dotenv import load_dotenv

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
from datetime import datetime

from app.modules.kenyalensiq.models import (
    KenyaLensUser,
    KenyaLensTenant,
    KenyaLensSubscription,
    KenyaLensAlert,
    KenyaLensBusiness,
    KenyaLensSurvey,
    KenyaLensAudit
)
from app.modules.auth.models import User as AuthUser
from app.modules.auth.service import get_current_user

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

app = FastAPI(title="EvidLens API", version="2.5.3")

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

from app.modules.cron.price_cron import start_scheduler
from app.modules.database import create_db_and_tables

@app.on_event("startup")
def on_startup():
    init_db()
    create_db_and_tables()
    # seed_data()
    start_scheduler()
    scheduler.add_job(scrape_kpin_prices, "cron", hour=6)
    scheduler.start()

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

@app.get("/dashboard")
def dashboard(
    request: Request,
    sub: Subscription = Depends(require_active_subscription)
):
    data = get_dashboard_data()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "data": data,
        "current_user": {"api_key": sub.api_key}
    })

PRICING = {
    "BASIC": {"monthly": 500, "yearly": 5000},
    "PROFESSIONAL": {"monthly": 1500, "yearly": 15000},
    "ENTERPRISE": {"monthly": 5000, "yearly": 50000}
}
ADDONS = {
    "EXTRA_REPORTS_10": {"name": "10 Extra Reports", "one_time": 1000},
    "API_ACCESS": {"name": "API Access", "monthly": 2000},
    "TEAM_SEAT": {"name": "Extra Team Seat", "monthly": 500},
    "DATA_EXPORT": {"name": "Bulk Data Export", "one_time": 5000}
}
ALC = {
    "CUSTOM_REPORT": {"name": "Custom Market Report", "price": 25000},
    "DATA_ONBOARDING": {"name": "Data Onboarding", "price": 50000},
    "TRAINING": {"name": "Team Training", "price": 15000}
}

def get_mpesa_token():
    api_url = (
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        if MPESA_ENV == "sandbox"
        else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    )
    r = requests.get(
        api_url,
        auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET)
    )
    return r.json()["access_token"]

def get_timestamp():
    return datetime.now().strftime('%Y%m%d%H%M%S')

def get_password(shortcode, passkey, timestamp):
    return base64.b64encode(
        (shortcode + passkey + timestamp).encode()
    ).decode('utf-8')

def get_session():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

get_db = get_session

def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
):
    user_id = request.cookies.get("user_id") or 1
    return int(user_id)

def get_subscription(db: Session, user_id: int):
    return db.exec(
        select(Subscription).where(Subscription.user_id == user_id)
    ).first()

def get_queries_today(db: Session, user_id: int):
    return len(
        db.exec(
            select(QueryLog).where(
                QueryLog.user_id == user_id,
                QueryLog.date == date.today()
            )
        ).all()
    )

def log_query(db: Session, user_id: int):
    db.add(QueryLog(user_id=user_id, date=date.today()))
    db.commit()

def check_subscription(user_id: int, db: Session):
    sub = get_subscription(db, user_id)
    if not sub or sub.status!= "active" or sub.expires_at < datetime.utcnow():
        if get_queries_today(db, user_id) >= 3:
            raise HTTPException(
                status_code=402,
                detail="Subscribe to continue. 3 free queries used."
            )
    return True

def generate_insights(user_message: str):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are EvidLens AI. You give market insights for Kenyan farmers and SMEs. Be concise and data-driven. Use KES and Counties."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}. Please try again."

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
            existing = session.exec(
                select(MarketPrice).where(
                    MarketPrice.product_name == row['product'],
                    MarketPrice.county == row['county'],
                    MarketPrice.market == row['market'],
                    func.date(MarketPrice.fetched_at) == datetime.utcnow().date()
                )
            ).first()
            if not existing:
                session.add(
                    MarketPrice(
                        product_name=row['product'],
                        price=row['price'],
                        county=row['county'],
                        market=row['market'],
                        fetched_at=datetime.utcnow()
                    )
                )
        session.commit()
    except Exception:
        pass
    finally:
        session.close()

@app.get("/market/risk")
def risk_sentinel(session: Session = Depends(get_session)):
    news = session.exec(
        select(
            NewsArticle.id,
            NewsArticle.product_name,
            NewsArticle.title,
            NewsArticle.timestamp,
            NewsArticle.url,
            NewsArticle.source,
            NewsArticle.published_at,
            NewsArticle.summary,
            NewsArticle.keywords,
            NewsArticle.fetched_at
        ).order_by(NewsArticle.published_at.desc()).limit(10)
    ).all()
    return {"risk_alerts": [dict(n._mapping) for n in news]}
@app.get("/market/export")
def export_navigator(session: Session = Depends(get_session)):
    exports = session.exec(select(ExportOpportunity).limit(20)).all()
    return {"export_opportunities": [e.dict() for e in exports]}

@app.post("/chat")
async def chat(
    payload: dict,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_subscription(user_id, db)
    db.add(
        MarketSearch(
            query=payload["message"],
            sector="All",
            county="Kenya",
            score=random.randint(50,100)
        )
    )
    db.commit()
    ai_response = generate_insights(payload["message"])
    log_query(db, user_id)
    return {"response": ai_response}

@app.get("/api/sectors")
def get_sectors(
    search: str = "",
    session: Session = Depends(get_session)
):
    q = select(Sector)
    if search:
        q = q.where(Sector.name.contains(search))
    return {"sectors": [s.name for s in session.exec(q).all()]}

@app.get("/api/counties")
def get_counties(
    search: str = "",
    session: Session = Depends(get_session)
):
    q = select(County)
    if search:
        q = q.where(County.name.contains(search))
    return {"counties": [c.name for c in session.exec(q).all()]}

@app.get("/api/subcounties")
def get_subcounties(
    county: str = "",
    search: str = "",
    session: Session = Depends(get_session)
):
    q = select(SubCounty)
    if county:
        q = q.join(County).where(County.name == county)
    if search:
        q = q.where(SubCounty.name.contains(search))
    return {"subcounties": [s.name for s in session.exec(q).all()]}

@app.get("/api/products")
def get_products(
    search: str = "",
    session: Session = Depends(get_session)
):
    q = select(FMCGProduct)
    if search:
        q = q.where(FMCGProduct.name.contains(search))
    return {"products": [p.name for p in session.exec(q).all()]}

@app.get("/api/companies")
def get_companies(
    search: str = "",
    sector: str = "",
    county: str = "",
    page: int = 1,
    limit: int = 10,
    sort_by: str = "rating",
    order: str = "desc",
    session: Session = Depends(get_session)
):
    q = select(Company)
    if search:
        q = q.where(
            or_(
                Company.name.ilike(f"%{search}%"),
                Company.sector.ilike(f"%{search}%"),
                Company.county.ilike(f"%{search}%")
            )
        )
    if sector:
        q = q.where(Company.sector == sector)
    if county:
        q = q.where(Company.county == county)
    all_data = session.exec(q).all()
    total = len(all_data)
    q = apply_sort(q, Company, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {
        "companies": [c.dict() for c in data],
        "total": total,
        "page": page
    }

@app.get("/api/prices")
def get_prices(
    search: str = "",
    product: str = "",
    county: str = "",
    page: int = 1,
    limit: int = 10,
    sort_by: str = "price",
    order: str = "desc",
    session: Session = Depends(get_session)
):
    q = select(MarketPrice)
    if search:
        q = q.where(
            or_(
                MarketPrice.product_name.contains(search),
                MarketPrice.county.contains(search)
            )
        )
    if product:
        q = q.where(MarketPrice.product_name == product)
    if county:
        q = q.where(MarketPrice.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketPrice, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {
        "prices": [p.dict() for p in data],
        "total": total,
        "page": page
    }

@app.get("/api/demand")
def get_demand(
    search: str = "",
    product: str = "",
    county: str = "",
    page: int = 1,
    limit: int = 10,
    sort_by: str = "demand_score",
    order: str = "desc",
    session: Session = Depends(get_session)
):
    q = select(MarketMetric)
    if search:
        q = q.where(
            or_(
                MarketMetric.product_name.contains(search),
                MarketMetric.county.contains(search)
            )
        )
    if product:
        q = q.where(MarketMetric.product_name == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {
        "demand": [m.dict() for m in data],
        "total": total,
        "page": page
    }

@app.get("/api/county-stats")
def get_county_stats(
    search: str = "",
    page: int = 1,
    limit: int = 47,
    sort_by: str = "market_size",
    order: str = "desc",
    session: Session = Depends(get_session)
):
    q = select(
        MarketMetric.county,
        func.sum(MarketMetric.market_size_kes).label("market_size"),
        func.avg(MarketMetric.growth_percent).label("growth"),
        func.sum(MarketMetric.volume).label("volume")
    ).group_by(MarketMetric.county)
    if search:
        q = q.where(MarketMetric.county.contains(search))
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    stats = [dict(r._mapping) for r in data]
    stats.sort(key=lambda x: x.get(sort_by, 0), reverse=(order=="desc"))
    return {
        "stats": stats,
        "total": 47,
        "page": page
    }

@app.get("/api/top-sectors")
def get_top_sectors(
    search: str = "",
    page: int = 1,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    q = select(
        MarketSearch.sector,
        func.count(MarketSearch.id).label("count")
    ).group_by(MarketSearch.sector)
    if search:
        q = q.where(MarketSearch.sector.contains(search))
    total = len(session.exec(q).all())
    data = session.exec(
        q.order_by(func.count(MarketSearch.id).desc())
      .offset((page-1)*limit).limit(limit)
    ).all()
    return {
        "sectors": [dict(r._mapping) for r in data],
        "total": total,
        "page": page
    }

@app.get("/api/opportunities")
def get_opportunities(
    search: str = "",
    product: str = "",
    county: str = "",
    page: int = 1,
    limit: int = 10,
    sort_by: str = "opportunity_score",
    order: str = "desc",
    session: Session = Depends(get_session)
):
    q = select(MarketMetric)
    if search:
        q = q.where(
            or_(
                MarketMetric.product_name.contains(search),
                MarketMetric.county.contains(search)
            )
        )
    if product:
        q = q.where(MarketMetric.product_name == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {
        "opportunities": [m.dict() for m in data],
        "total": total,
        "page": page
    }

class DetailedAnalysisRequest(BaseModel):
    product: str
    sector: str
    county: str
    subcounty: str = ""
    budget_kes: float = 0
    business_model: str = "Retail"

@app.post("/api/analyze-detailed")
async def analyze_detailed(
    req: DetailedAnalysisRequest,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    check_subscription(user_id, db)
    competitors = db.exec(
        select(Company)
      .where(
            Company.sector==req.sector,
            Company.county==req.county
        ).limit(10)
    ).all()
    prices = db.exec(
        select(MarketPrice)
      .where(
            MarketPrice.product_name.contains(req.product),
            MarketPrice.county==req.county
        ).limit(5)
    ).all()
    demand = db.exec(
        select(MarketMetric)
      .where(
            MarketMetric.product_name.contains(req.product),
            MarketMetric.county==req.county
        ).first()
    )
    prompt = (
        f"Product: {req.product} "
        f"Sector: {req.sector} "
        f"Location: {req.subcounty}, {req.county} "
        f"Budget: KES {req.budget_kes} "
        f"Model: {req.business_model} "
        f"Competitors: {[c.name for c in competitors]} "
        f"Avg Price: {[p.price for p in prices]} "
        f"Demand Score: {demand.demand_score if demand else 'N/A'} "
        f"Market Size: KES {demand.market_size_kes if demand else 'N/A'}"
    )
    ai_response = generate_insights(prompt)
    log_query(db, user_id)
    return {
        "summary": ai_response,
        "competitors": [c.dict() for c in competitors],
        "prices": [p.dict() for p in prices],
        "demand": demand.dict() if demand else None
    }

@app.get("/api/export/{table}")
def export_csv(
    table: str,
    search: str = "",
    session: Session = Depends(get_session)
):
    output = io.StringIO()
    writer = csv.writer(output)
    if table == "companies":
        q = select(Company)
        data = session.exec(q).all()
        writer.writerow(
            ["Name","Sector","County","Rating","Reviews","Address","Lat","Lng"]
        )
        [
            writer.writerow([
                r.name,r.sector,r.county,r.rating,r.reviews,r.address,r.lat,r.lng
            ]) for r in data
        ]
    elif table == "prices":
        q = select(MarketPrice)
        data = session.exec(q).all()
        writer.writerow(["Product","Price","County","Market","Source","FetchedAt"])
        [
            writer.writerow([
                r.product_name,r.price,r.county,r.market,r.source,r.fetched_at
            ]) for r in data
        ]
    elif table == "demand":
        q = select(MarketMetric)
        data = session.exec(q).all()
        writer.writerow(
            ["Product","Sector","County","DemandScore","MarketSizeKES","Growth%","Volume","OpportunityScore"]
        )
        [
            writer.writerow([
                r.product_name,r.sector,r.county,r.demand_score,
                r.market_size_kes,r.growth_percent,r.volume,r.opportunity_score
            ]) for r in data
        ]
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"}
    )

@app.get("/api/social-feed")
def get_social_feed(
    platform: str = "all",
    session: Session = Depends(get_session)
):
    q = select(SocialPost).order_by(SocialPost.created_at.desc()).limit(20)
    if platform!= "all":
        q = q.where(SocialPost.platform == platform)
    return {"posts": [p.dict() for p in session.exec(q).all()]}

@app.get("/api/news-feed")
def get_news_feed(session: Session = Depends(get_session)):
    return {
        "articles": [
            n.dict() for n in session.exec(
                select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(20)
            ).all()
        ]
    }

def dashboard_api(session: Session):
    company_count = session.exec(select(func.count(LensBusiness.id))).one()
    metric_count = session.exec(select(func.count(MarketMetric.id))).one()
    search_count = session.exec(select(func.count(MarketSearch.id))).one()
    county_count = session.exec(select(func.count(County.id))).one()
    social_count = session.exec(select(func.count(SocialPost.id))).one()
    news_count = session.exec(select(func.count(NewsArticle.id))).one()
    sector_count = session.exec(select(func.count(Sector.id))).one()
    product_count = session.exec(select(func.count(FMCGProduct.id))).one()
    subscription_count = session.exec(select(func.count(Subscription.id))).one()
    policy_count = session.exec(select(func.count(PolicyWatch.id))).one()
    export_count = session.exec(select(func.count(ExportOpportunity.id))).one()
    funding_count = session.exec(
        select(func.count(Company.id)).where(
            or_(
                Company.sector.contains("Financial"),
                Company.sector.contains("Banking"),
                Company.sector.contains("Insurance"),
                Company.sector.contains("SACCO"),
                Company.sector.contains("Microfinance"),
                Company.sector.contains("FinTech")
            )
        )
    ).one()

    lens_count = session.exec(select(func.count()).select_from(LensSurvey)).one()
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
        "active_products": product_count
    }

    top_demands = session.exec(
        select(
            MarketMetric.product_name,
            MarketMetric.county,
            MarketMetric.sector,
            MarketMetric.demand_score
        ).order_by(desc(MarketMetric.demand_score)).limit(3)
    ).all()

    trending = []
    for d in top_demands:
        trending.append(
            {
                "category": d.sector or 'Agriculture',
                "headline": f"{d.product_name} demand up in {d.county}",
                "score": d.demand_score,
                "product": d.product_name,
                "county": d.county,
                "updated": ""
            }
        )
    if not trending:
        trending = [{"category": "Agriculture", "headline": "No data yet", "score": 0}]
    return {
        "stats": stats,
        "trending": trending,
        "modules": modules,
        "last_updated": datetime.utcnow().isoformat()
    }

@app.get("/api/pricing")
def api_pricing():
    return {
        "plans": PRICING,
        "addons": ADDONS,
        "alc": ALC
    }

@app.post("/api/checkout")
def mpesa_stk_push(
    payload: dict,
    user_id: int = Depends(get_current_user)
):
    plan = payload.get("plan")
    billing = payload.get("billing")
    phone = payload.get("phone")
    amount = PRICING[billing]
    token = get_mpesa_token()
    timestamp = get_timestamp()
    password = get_password(MPESA_SHORTCODE, MPESA_PASSKEY, timestamp)
    api_url = (
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        if MPESA_ENV == "sandbox"
        else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    )
    headers = {"Authorization": "Bearer " + token}
    payload_mpesa = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": f"EvidLens-{plan}-{user_id}",
        "TransactionDesc": f"{plan} {billing} Subscription"
    }
    r = requests.post(api_url, json=payload_mpesa, headers=headers)
    return r.json()

@app.post("/api/mpesa-callback")
async def mpesa_callback(
    request: Request,
    db: Session = Depends(get_db)
):
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
                sub.mpesa_receipt = items["MpesaReceiptNumber"]
            else:
                db.add(
                    Subscription(
                        user_id=user_id,
                        plan=plan,
                        status="active",
                        expires_at=expires,
                        mpesa_receipt=items["MpesaReceiptNumber"]
                    )
                )
            db.add(
                MpesaTransaction(
                    user_id=user_id,
                    phone=items["PhoneNumber"],
                    amount=items["Amount"],
                    receipt=items["MpesaReceiptNumber"],
                    checkout_id=stk["CheckoutRequestID"],
                    plan=plan,
                    status="SUCCESS"
                )
            )
            db.commit()
    except Exception:
        pass
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.post("/api/run-scraper")
def run_scraper():
    scrape_kpin_prices()
    return {"status": "scraper ran. DB updated with real prices"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.5.3"}

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(
        "pricing.html",
        {"request": request, "plans": PRICING, "addons": ADDONS, "alc": ALC}
    )

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

@app.get("/undefined")
def catch_undefined():
    return {"status": "ignored"}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, session: Session = Depends(get_session)):
    data = dashboard_api(session)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data}
    )

@app.get("/competitive", response_class=HTMLResponse)
def competitive_page(request: Request, session: Session = Depends(get_session)):
    companies = session.exec(select(Company).limit(50)).all()
    return templates.TemplateResponse(
        "competitive.html", 
        {"request": request, "companies": companies}
    )

@app.get("/market/prices", response_class=HTMLResponse)  
def prices_page(request: Request, session: Session = Depends(get_session)):
    prices = session.exec(select(MarketPrice).order_by(MarketPrice.fetched_at.desc()).limit(100)).all()
    return templates.TemplateResponse(
        "prices.html", 
        {"request": request, "prices": prices}
    )

@app.get("/market/demand", response_class=HTMLResponse)
def demand_page(request: Request, session: Session = Depends(get_session)):
    demand = session.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
    return templates.TemplateResponse(
        "demand.html", 
        {"request": request, "demand": demand}
    )

@app.get("/location/counties", response_class=HTMLResponse)
def counties_page(request: Request, session: Session = Depends(get_session)):
    counties = session.exec(select(County)).all()
    stats = session.exec(
        select(
            MarketMetric.county,
            func.sum(MarketMetric.market_size_kes).label("market_size")
        ).group_by(MarketMetric.county)
    ).all()
    return templates.TemplateResponse(
        "counties.html", 
        {"request": request, "counties": counties, "stats": [dict(s._mapping) for s in stats]}
    )

@app.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request, session: Session = Depends(get_session)):
    posts = session.exec(select(SocialPost).order_by(SocialPost.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse(
        "voice.html", 
        {"request": request, "posts": posts}
    )

@app.get("/kb/policy", response_class=HTMLResponse)
def policy_page(request: Request, session: Session = Depends(get_session)):
    policies = session.exec(select(PolicyWatch).order_by(PolicyWatch.published_at.desc()).limit(20)).all()
    return templates.TemplateResponse(
        "policy.html", 
        {"request": request, "policies": policies}
    )

@app.get("/reports/funding", response_class=HTMLResponse)
def funding_page(request: Request, session: Session = Depends(get_session)):
    funders = session.exec(
        select(Company).where(
            or_(
                Company.sector.contains("Financial"),
                Company.sector.contains("Banking"),
                Company.sector.contains("Insurance"),
                Company.sector.contains("SACCO")
            )
        ).limit(50)
    ).all()
    return templates.TemplateResponse(
        "funding.html", 
        {"request": request, "funders": funders}
    )

@app.get("/kenyalensiq")
def kenyalsiq_dashboard(session: Session = Depends(get_session)):
    business_count = session.exec(select(func.count()).select_from(LensBusiness)).one()
    survey_count = session.exec(select(func.count()).select_from(LensSurvey)).one()
    response_count = session.exec(select(func.count()).select_from(LensResponse)).one()
    tenant_count = session.exec(select(func.count()).select_from(Tenant)).one()
    user_count = session.exec(select(func.count()).select_from(User)).one()

    return {
        "title": "KenyaLensIQ",
        "modules": [
            {"id": 1, "name": "Businesses", "icon": "🏢", "count": business_count, "route": "/businesses"},
            {"id": 2, "name": "Surveys", "icon": "📋", "count": survey_count, "route": "/surveys"},
            {"id": 3, "name": "Responses", "icon": "📝", "count": response_count, "route": "/responses"},
            {"id": 4, "name": "Tenants", "icon": "🏛️", "count": tenant_count, "route": "/tenants"},
            {"id": 5, "name": "Users", "icon": "👥", "count": user_count, "route": "/users"},
        ]
    }

@app.get("/dashboard")
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    data = get_dashboard_data(current_user.tenant_id)
    
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
        "export": "/api/export"
    }
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "data": data,
        "API": API
    })
    
@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("settings.html", {"request": request, "current_user": user})
@app.get("/billing", response_class=HTMLResponse)
def billing(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("billing.html", {"request": request, "current_user": user, "plans": PRICING})
@app.get("/security", response_class=HTMLResponse)
def security(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("security.html", {"request": request, "current_user": user})
@app.get("/history", response_class=HTMLResponse)
def history(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("history.html", {"request": request, "current_user": user})
@app.get("/stats", response_class=HTMLResponse)
def stats(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("stats.html", {"request": request, "current_user": user})
@app.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("wallet.html", {"request": request, "current_user": user})
@app.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("workspaces.html", {"request": request, "current_user": user})
@app.get("/help", response_class=HTMLResponse)
def help(request: Request): return templates.TemplateResponse("help.html", {"request": request})
@app.get("/changelog", response_class=HTMLResponse)
def changelog(request: Request): return templates.TemplateResponse("changelog.html", {"request": request})
@app.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request): return templates.TemplateResponse("forgot.html", {"request": request})
@app.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, token: str): return templates.TemplateResponse("reset.html", {"request": request, "token": token})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
