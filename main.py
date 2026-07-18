from fastapi import FastAPI, Request, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from dotenv import load_dotenv
from sqlmodel import Session
import os

load_dotenv()

from app.modules.database import init_database, get_session
from app.modules.cron.price_cron import start_scheduler

from app.modules.auth.models import User, UserRole
from app.modules.models import Sector, County, CoreProduct
from app.modules.payments.models import Payment, Subscription, MpesaTransaction
from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
from app.modules.market_engine.models import MarketSearch, MarketMetric
from app.modules.core.models import Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter

from app.modules.auth.router import router as auth_router
from app.modules.payments.router import router as payments_router
from app.modules.market_engine.router import router as market_router
from app.modules.consumer_voice.router import router as consumer_router
from app.modules.data_layer.router import router as data_router
from app.modules.ai_insights.router import router as ai_router
from app.modules.report_builder.router import router as report_router
from app.modules.location_intel.router import router as location_router
from app.modules.knowledge_base.router import router as knowledge_router
from app.modules.business_os.router import router as business_router
from app.modules.rag.router import router as rag_router
from app.modules.web import routes as web_routes

# IMPORT THE SERVICE FUNCTIONS
from app.modules.market_engine.service import search_market, get_dashboard_stats, get_real_time_terminal, get_competitor_overview, get_location_data
from app.modules.core.service import get_all_pricing, PRICING, ADDONS, ALC

app = FastAPI(title="EvidLens API", version="2.0.0", description="Kenya's Decision Intelligence Platform - 9 Lanes, 19 Modules. All 75 Sectors.")

@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])
app.include_router(market_router, prefix="/market", tags=["Market Engine"])
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

# ========== DASHBOARD ENDPOINTS ==========

@app.get("/api/dashboard")
async def dashboard(db: Session = Depends(get_session)):
    return get_dashboard_stats(db)

@app.post("/search-market")
async def search(q: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_session)):
    data = search_market(db, q, sector, county)
    data["ai_insight"] = await analyze_with_ai(data)
    html = f"<div class='p-3 bg-white rounded border-gray-200'><h3 class='font-bold text-lg' style='color:#0A1F44'>{data['query']}</h3><p>Demand: <b style='color:#14B8A6'>{data['demand_level']}</b></p><p>Market Size: <b>KES {data['market_size_kes']:,}</b></p><p>Avg Price: <b>KES {data['price_range']['avg']:,}</b></p><p>Competitors Found: <b>{data['competitor_count']}</b></p><hr class='my-3'><p style='color:#0A1F44'>{data['ai_insight']}</p></div>"
    return HTMLResponse(html)

@app.post("/chat")
async def chat(payload: dict, db: Session = Depends(get_session)):
    msg = payload.get("message")
    context = payload.get("context")
    prompt = f"You are Lens, EvidLens AI. Context: Business={context}. Question: {msg}. Answer in 2-3 sentences with Kenya data."
    reply = await call_groq(prompt)
    return {"reply": reply}

# ========== MONETIZATION ENDPOINTS ==========

@app.get("/api/pricing")
def api_pricing(db: Session = Depends(get_session)):
    return get_all_pricing(db)

@app.post("/api/checkout")
def checkout(payload: dict, db: Session = Depends(get_session)):
    plan_name = payload.get("plan")
    billing = payload.get("billing") # "monthly" or "annual"
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
