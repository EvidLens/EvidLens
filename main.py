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
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from groq import Groq
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, date

from app.modules.kenyalensiq.models import (
    MarketMetric, PriceData, NewsArticle, SocialMention,
    KenyaTenant, KenyaLensBusiness, KenyaLensSurvey,
    KenyaLensSubscription, KenyaLensAlert, KenyaLensMember
)
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user, require_active_subscription

load_dotenv()

from app.modules.database import engine, create_db_and_tables
from app.modules.db import init_db
from app.modules.cron.price_cron import start_scheduler
from app.modules.kenyalensiq.router import router as kenyalensiq_router
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

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")
MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
client = Groq(api_key=GROQ_API_KEY)

app.include_router(kenyalensiq_router, prefix="/kenyalensiq", tags=["kenyalensiq"])
app.include_router(competitive_router)
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

def get_session():
    db = Session(engine)
    try: yield db
    finally: db.close()

PRICING = {"BASIC": {"monthly": 500, "yearly": 5000}, "PROFESSIONAL": {"monthly": 1500, "yearly": 15000}, "ENTERPRISE": {"monthly": 5000, "yearly": 50000}}
ADDONS = {"EXTRA_REPORTS_10": {"name": "10 Extra Reports", "one_time": 1000}, "API_ACCESS": {"name": "API Access", "monthly": 2000}, "TEAM_SEAT": {"name": "Extra Team Seat", "monthly": 500}, "DATA_EXPORT": {"name": "Bulk Data Export", "one_time": 5000}}
ALC = {"CUSTOM_REPORT": {"name": "Custom Market Report", "price": 25000}, "DATA_ONBOARDING": {"name": "Data Onboarding", "price": 50000}, "TRAINING": {"name": "Team Training", "price": 15000}}

def get_mpesa_token():
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(api_url, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return r.json()["access_token"]

def get_timestamp(): return datetime.now().strftime('%Y%m%d%H%M%S')
def get_password(shortcode, passkey, timestamp): return base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')
def apply_sort(q, model, sort_by: str, order: str):
    if not sort_by or not hasattr(model, sort_by): return q
    col = getattr(model, sort_by)
    return q.order_by(desc(col) if order == "desc" else asc(col))

def generate_insights(user_message: str):
    try:
        completion = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": "You are EvidLens AI. You give market insights for Kenyan farmers and SMEs. Be concise and data-driven. Use KES and Counties."}, {"role": "user", "content": user_message}])
        return completion.choices[0].message.content
    except Exception as e: return f"AI Error: {str(e)}. Please try again."

def get_dashboard_data(session: Session):
    business_count = session.exec(select(func.count(KenyaLensBusiness.id))).one()
    metric_count = session.exec(select(func.count(MarketMetric.id))).one()
    price_count = session.exec(select(func.count(PriceData.id))).one()
    news_count = session.exec(select(func.count(NewsArticle.id))).one()
    social_count = session.exec(select(func.count(SocialMention.id))).one()
    tenant_count = session.exec(select(func.count(KenyaTenant.id))).one()
    survey_count = session.exec(select(func.count(KenyaLensSurvey.id))).one()
    subscription_count = session.exec(select(func.count(KenyaLensSubscription.id))).one()

    modules = [
        {"id": 1, "name": "Competitive Engine", "icon": "🎯", "count": business_count, "route": "/competitive"},
        {"id": 2, "name": "Price Oracle", "icon": "💰", "count": price_count, "route": "/market/prices"},
        {"id": 3, "name": "Demand Radar", "icon": "📈", "count": metric_count, "route": "/market/demand"},
        {"id": 4, "name": "County Mapper", "icon": "🗺️", "count": tenant_count, "route": "/location/counties"},
        {"id": 5, "name": "Consumer Pulse", "icon": "👥", "count": social_count, "route": "/voice"},
        {"id": 6, "name": "Risk Sentinel", "icon": "⚠️", "count": news_count, "route": "/market/risk"},
        {"id": 7, "name": "Policy Watch", "icon": "📜", "count": news_count, "route": "/kb/policy"},
        {"id": 8, "name": "Funding Radar", "icon": "🏦", "count": business_count, "route": "/reports/funding"},
        {"id": 9, "name": "Export Navigator", "icon": "🚢", "count": metric_count, "route": "/market/export"},
        {"id": 10, "name": "KenyaLensIQ", "icon": "📊", "count": survey_count, "route": "/kenyalensiq"}
    ]
    stats = {"insights_generated": metric_count, "sectors_covered": 12, "reports_exported": subscription_count, "active_products": price_count}
    top_demands = session.exec(select(MarketMetric.product_name, MarketMetric.county, MarketMetric.sector, MarketMetric.demand_score).order_by(desc(MarketMetric.demand_score)).limit(1)).all()
    trending = {"category": top_demands[0].sector if top_demands else "Agriculture", "headline": f"{top_demands[0].product_name} demand up in {top_demands[0].county}" if top_demands else "No data yet"}
    return {"stats": stats, "trending": trending, "modules": modules, "last_updated": datetime.utcnow().isoformat()}

@app.on_event("startup")
def on_startup():
    init_db()
    create_db_and_tables()
    start_scheduler()

@app.get("/")
async def root(request: Request, session: Session = Depends(get_session)):
    data = get_dashboard_data(session)
    API = {"logout": "/auth/logout", "login": "/login", "prices": "/api/prices", "demand": "/api/demand", "companies": "/api/companies", "county_stats": "/api/county-stats", "sectors": "/api/top-sectors", "opportunities": "/api/opportunities", "get_sectors": "/api/sectors", "get_counties": "/api/counties", "get_subcounties": "/api/subcounties", "analyze": "/api/analyze-detailed", "chat": "/chat", "download": "/download-report", "export": "/api/export"}
    return templates.TemplateResponse("dashboard.html", {"request": request, "data": data, "API": API, "current_user": None})

@app.get("/dashboard")
async def dashboard(request: Request, current_user: AuthUser = Depends(get_current_user), session: Session = Depends(get_session)):
    data = get_dashboard_data(session)
    API = {"logout": "/auth/logout", "login": "/login", "prices": "/api/prices", "demand": "/api/demand", "companies": "/api/companies", "county_stats": "/api/county-stats", "sectors": "/api/top-sectors", "opportunities": "/api/opportunities", "get_sectors": "/api/sectors", "get_counties": "/api/counties", "get_subcounties": "/api/subcounties", "analyze": "/api/analyze-detailed", "chat": "/chat", "download": "/download-report", "export": "/api/export"}
    return templates.TemplateResponse("dashboard.html", {"request": request, "current_user": current_user, "data": data, "API": API})

@app.get("/api/sectors")
def get_sectors(search: str = "", session: Session = Depends(get_session)):
    return {"sectors": list(set([m.sector for m in session.exec(select(MarketMetric)).all() if m.sector]))}

@app.get("/api/counties")
def get_counties(search: str = "", session: Session = Depends(get_session)):
    return {"counties": list(set([m.county for m in session.exec(select(MarketMetric)).all() if m.county]))}

@app.get("/api/subcounties")
def get_subcounties(county: str = "", search: str = "", session: Session = Depends(get_session)):
    return {"subcounties": []}

@app.get("/api/prices")
def get_prices(search: str = "", page: int = 1, limit: int = 15, sort_by: str = "price", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    total = len(session.exec(q).all())
    data = session.exec(apply_sort(q, MarketMetric, sort_by, order).offset((page-1)*limit).limit(limit)).all()
    return {"prices": [{"product": d.product_name, "price": d.avg_price_kes, "county": d.county, "market": d.county, "fetched_at": d.timestamp.isoformat()} for d in data], "total": total, "page": page}

@app.get("/api/demand")
def get_demand(search: str = "", page: int = 1, limit: int = 15, sort_by: str = "demand_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    total = len(session.exec(q).all())
    data = session.exec(apply_sort(q, MarketMetric, sort_by, order).offset((page-1)*limit).limit(limit)).all()
    return {"demand": [d.dict() for d in data], "total": total, "page": page}

@app.get("/api/companies")
def get_companies(search: str = "", page: int = 1, limit: int = 10, sort_by: str = "rating", order: str = "desc", session: Session = Depends(get_session)):
    q = select(KenyaLensBusiness)
    total = len(session.exec(q).all())
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": [c.dict() for c in data], "total": total, "page": page}

@app.get("/api/county-stats")
def get_county_stats(search: str = "", page: int = 1, limit: int = 47, sort_by: str = "market_size", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric.county, func.sum(MarketMetric.market_size_kes).label("market_size"), func.avg(MarketMetric.growth_percent).label("growth"), func.sum(MarketMetric.volume).label("volume")).group_by(MarketMetric.county)
    data = session.exec(q).all()
    stats = [dict(r._mapping) for r in data]
    return {"stats": stats, "total": len(stats), "page": page}

@app.get("/api/top-sectors")
def get_top_sectors(search: str = "", page: int = 1, limit: int = 10, session: Session = Depends(get_session)):
    return {"sectors": [], "total": 0, "page": page}

@app.get("/api/opportunities")
def get_opportunities(search: str = "", page: int = 1, limit: int = 10, sort_by: str = "opportunity_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    total = len(session.exec(q).all())
    data = session.exec(apply_sort(q, MarketMetric, sort_by, order).offset((page-1)*limit).limit(limit)).all()
    return {"opportunities": [d.dict() for d in data], "total": total, "page": page}

class DetailedAnalysisRequest(BaseModel):
    product: str; sector: str; county: str; subcounty: str = ""; budget_kes: float = 0; business_model: str = "Retail"

@app.post("/api/analyze-detailed")
async def analyze_detailed(req: DetailedAnalysisRequest, current_user: AuthUser = Depends(get_current_user)):
    prompt = f"Product: {req.product} Sector: {req.sector} Location: {req.county} Budget: KES {req.budget_kes}"
    ai_response = generate_insights(prompt)
    return {"summary": ai_response, "competitors": [], "prices": [], "demand": None}

@app.get("/api/export/{table}")
def export_csv(table: str, search: str = "", session: Session = Depends(get_session)):
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["Data"]); output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"})

@app.post("/chat")
async def chat(payload: dict, current_user: AuthUser = Depends(get_current_user)):
    ai_response = generate_insights(payload["message"])
    return {"reply": ai_response}

@app.get("/health")
def health(): return {"status": "healthy", "version": "2.5.3"}
@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request): return templates.TemplateResponse("pricing.html", {"request": request, "plans": PRICING, "addons": ADDONS, "alc": ALC})
@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request): return templates.TemplateResponse("privacy.html", {"request": request})
@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request): return templates.TemplateResponse("terms.html", {"request": request})
@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request): return templates.TemplateResponse("contact.html", {"request": request})
@app.get("/about", response_class=HTMLResponse)
def about(request: Request): return templates.TemplateResponse("about.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
