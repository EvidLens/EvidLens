from fastapi import FastAPI, Request, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from dotenv import load_dotenv
from sqlmodel import Session, select
from sqlalchemy import func, distinct
import os
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

load_dotenv()

AT_API_KEY = os.getenv("AT_API_KEY")
AT_USERNAME = os.getenv("AT_USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL")
ENV = os.getenv("ENV", "development")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")

from app.modules.db import init_db
from app.modules.database import get_session
from app.modules.cron.price_cron import start_scheduler

from app.modules.auth.models import User, UserRole
from app.modules.models import Sector, County, CoreProduct
from app.modules.payments.models import Payment, Subscription, MpesaTransaction
from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
from app.modules.market_engine.models import MarketSearch, MarketMetric
from app.modules.competitive_engine.models import Company, FundingDeal, TrafficSnapshot
from app.modules.core.models import Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter

from app.modules.auth.router import router as auth_router
from app.modules.payments.router import router as payments_router
from app.modules.market_engine.router import router as market_router
from app.modules.competitive_engine.router import router as competitive_router
from app.modules.consumer_voice.router import router as consumer_router
from app.modules.data_layer.router import router as data_router
from app.modules.ai_insights.router import router as ai_router
from app.modules.report_builder.router import router as report_router
from app.modules.location_intel.router import router as location_router
from app.modules.knowledge_base.router import router as knowledge_router
from app.modules.business_os.router import router as business_router
from app.modules.rag.router import router as rag_router
from app.modules.web import routes as web_routes

from app.modules.market_engine.service import search_market, get_real_time_terminal, get_competitor_overview, get_location_data
from app.modules.core.service import get_all_pricing, PRICING, ADDONS, ALC

app = FastAPI(title="EvidLens API", version="2.0.0", description="Kenya's Decision Intelligence Platform - 9 Lanes, 19 Modules. All 75 Sectors.")

scheduler = AsyncIOScheduler()

async def fetch_prices_from_AIT():
    try:
        url = "https://api.africastalking.com/version1/ussd"
        headers = {"apiKey": AT_API_KEY, "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        data = {"username": AT_USERNAME, "phoneNumber": "+254700000", "serviceCode": "*384*1#"}
        requests.post(url, headers=headers, data=data, timeout=15)
    except:
        pass

async def fetch_news_from_NEWSAPI():
    try:
        url = f"https://newsapi.org/v2/everything?q=Kenya agriculture OR maize OR milk&language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize=20"
        requests.get(url, timeout=10)
    except:
        pass

async def fetch_tweets_from_X():
    try:
        if not X_BEARER_TOKEN:
            return
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
        params = {"query": "Kenya agriculture OR maize price OR unga OR milk -is:retweet lang:en", "tweet.fields": "author_id,created_at", "max_results": 20}
        requests.get(url, headers=headers, params=params, timeout=10)
    except:
        pass

async def run_groq_analysis():
    try:
        prompt = "Summarize Kenyan agriculture market trends in 3 bullets for business owners"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]}
        requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=15)
    except:
        pass

async def send_email_resend(to, subject, html):
    try:
        url = "https://api.resend.com/emails"
        headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}
        data = {"from": "EvidLens <noreply@evidlens.com>", "to": [to], "subject": subject, "html": html}
        requests.post(url, headers=headers, json=data, timeout=10)
    except:
        pass

async def fetch_all_data():
    await fetch_prices_from_AIT()
    await fetch_news_from_NEWSAPI()
    await fetch_tweets_from_X()
    await run_groq_analysis()

@app.on_event("startup")
async def on_startup():
    init_db()
    start_scheduler()
    await fetch_all_data()
    scheduler.add_job(fetch_all_data, "interval", hours=1)
    scheduler.start()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])
app.include_router(market_router, prefix="/market", tags=["Market Engine"])
app.include_router(competitive_router, prefix="/competitive", tags=["Competitive Engine"])
app.include_router(consumer_router, prefix="/voice", tags=["Consumer Voice"])
app.include_router(data_router, prefix="/data", tags=["Data Layer"])
app.include_router(ai_router, prefix="/ai", tags=["AI Insights"])
app.include_router(report_router, prefix="/reports", tags=["Report Builder"])
app.include_router(location_router, prefix="/location", tags=["Location Intel"])
app.include_router(knowledge_router, prefix="/kb", tags=["Knowledge Base"])
app.include_router(business_router, prefix="/os", tags=["Business OS"])
app.include_router(rag_router, prefix="/api", tags=["RAG"])
app.include_router(web_routes.router)

@app.exception_handler(500)
async def internal_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0", "sectors": 75, "modules": 19}

def get_dashboard_stats(db: Session):
    try:
        insights_generated = db.query(MarketSearch).count()
        active_products = db.query(distinct(MarketMetric.product_name)).count()
        sectors_covered = db.query(distinct(Company.sector)).count()
        reports_exported = 0
        return {
            "insights_generated": insights_generated,
            "active_products": active_products,
            "sectors_covered": sectors_covered,
            "reports_exported": reports_exported
        }
    except:
        return {
            "insights_generated": 0,
            "active_products": 0,
            "sectors_covered": 0,
            "reports_exported": 0
        }

@app.get("/api/dashboard")
def dashboard_api(session: Session = Depends(get_session)):
    return {"status": "LIVE", "stats": get_dashboard_stats(session)}

@app.get("/api/plans")
def get_plans(session: Session = Depends(get_session)):
    plans = session.query(Plan).all()
    return plans

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})

@app.get("/auth/me")
def get_current_user(request: Request, session: Session = Depends(get_session)):
    user_id = request.cookies.get("user_id") or 1
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    subscription = session.query(UserSubscription).filter(UserSubscription.user_id == user.id).first()
    return {"id": user.id, "email": user.email, "name": user.name, "plan": subscription.plan.name if subscription else "FREE", "reports_left": subscription.reports_left if subscription else 1, "avatar": user.avatar_url}

@app.get("/api/notifications")
def get_notifications(request: Request, session: Session = Depends(get_session)):
    user_id = request.cookies.get("user_id") or 1
    reports = session.query(Report).filter(Report.user_id == user_id, Report.status == "ready").limit(3).all()
    payments = session.query(MpesaTransaction).filter(MpesaTransaction.user_id == user_id, MpesaTransaction.status == "SUCCESS").limit(2).all()
    items = []
    for r in reports:
        items.append({"id": f"r{r.id}", "message": f"Your {r.sector} Report for {r.county} is ready", "link": f"/reports/{r.id}"})
    for p in payments:
        items.append({"id": f"p{p.id}", "message": f"M-Pesa payment of KES {p.amount} confirmed", "link": "/billing"})
    return {"count": len(items), "items": items}

@app.post("/auth/logout")
def logout():
    response = JSONResponse(content={"status": "logged_out"})
    response.delete_cookie("user_id")
    return response

@app.post("/search-market")
def search_market_endpoint(request: Request, session: Session = Depends(get_session)):
    return {"status": "ok"}

@app.post("/chat")
async def chat(payload: dict, session: Session = Depends(get_session)):
    msg = payload.get("message")
    context = payload.get("context")
    prompt = f"You are Lens, EvidLens AI. Context: Business={context}. Question: {msg}. Answer in 2-3 sentences with Kenya data."
    reply = await call_groq(prompt)
    return {"reply": reply}

@app.get("/api/pricing")
def api_pricing(session: Session = Depends(get_session)):
    return get_all_pricing(session)

@app.post("/api/checkout")
def checkout(payload: dict, session: Session = Depends(get_session)):
    plan_name = payload.get("plan")
    billing = payload.get("billing")
    amount = PRICING[plan_name][billing]
    return {"status": "ok", "plan": plan_name, "billing": billing, "amount": amount, "mpesa_prompt": f"Pay KES {amount:,}"}

@app.post("/api/buy-addon")
def buy_addon(payload: dict):
    addon = payload.get("addon")
    amount = ADDONS[addon].get("annual") or ADDONS[addon].get("one_time") or ADDONS[addon].get("setup")
    return {"status": "ok", "addon": addon, "amount": amount, "mpesa_prompt": f"Pay KES {amount:,}"}

@app.post("/api/buy-alc")
def buy_alc(payload: dict):
    service = payload.get("service")
    amount = ALC[service]["price"]
    return {"status": "ok", "service": service, "amount": amount, "mpesa_prompt": f"Pay KES {amount:,}"}

async def analyze_with_ai(data):
    prompt = f"Analyze this Kenyan market data: {data}. Give 2 sentence insight."
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
    data = r.json()
    return data["choices"][0]["message"]["content"] if "choices" in data else "AI unavailable"

async def call_groq(prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers, timeout=15)
    data = r.json()
    return data["choices"][0]["message"]["content"] if "choices" in data else "AI unavailable"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
