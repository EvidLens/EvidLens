from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc, or_
from datetime import datetime, timedelta
import secrets
import os

from app.core.db import get_session, get_db
from app.core.models import User, MarketMetric, NewsArticle, SocialMention, Company, ExportOpportunity
from app.modules.auth.dependencies import get_current_user
from app.core.service import _core
from main import dashboard_api, send_email, get_password_hash, LensEngineService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

PRICING = _core.PRICING
ADDONS = _core.ADDONS
ALC = _core.ALC

API_DICT = {"logout": "/auth/logout","login": "/login","prices": "/api/prices","demand": "/api/demand","companies": "/api/companies","county_stats": "/api/county-stats","sectors": "/api/top-sectors","opportunities": "/api/opportunities","get_sectors": "/api/data/sectors","get_counties": "/api/data/counties","get_subcounties": "/api/data/subcounties","analyze": "/api/analyze-detailed","chat": "/lens/chat","download": "/download-report","export": "/api/export"}

@router.get("/", response_class=HTMLResponse)
async def root(request: Request, session: Session = Depends(get_session)):
    data = dashboard_api(session)
    return templates.TemplateResponse("dashboard.html", {"request": request, "data": data, "API": API_DICT, "current_user": None})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    data = dashboard_api(session)
    API = {"logout": "/auth/logout","login": "/login","prices": "/api/prices","demand": "/api/demand","companies": "/api/companies","county_stats": "/api/county-stats","sectors": "/api/top-sectors","opportunities": "/api/opportunities","get_sectors": "/api/data/sectors","get_counties": "/api/data/counties","get_subcounties": "/api/data/subcounties","analyze": "/api/analyze-detailed","chat": "/lens/chat","download": "/download-report","export": "/api/export"}
    return templates.TemplateResponse("dashboard.html", {"request": request, "current_user": current_user, "data": data, "API": API})

@router.get("/api/billing/my-subscription")
async def my_subscription(user: User = Depends(get_current_user)):
    return {"plan": getattr(user, 'plan', 'Trial'), "modules": ["market-intel","location-intel","price-intel","demand-intel","competitor-intel","opportunity-intel","trade-intel","risk-intel","finance-intel","marketing-intel","supply-intel","export-intel"]}

@router.get("/market/risk", response_class=HTMLResponse)
def risk_sentinel_page(request: Request, session: Session = Depends(get_session)):
    news = session.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(10)).all()
    return templates.TemplateResponse("risk.html", {"request": request, "risk_alerts": [n.dict() for n in news]})

@router.get("/market/export", response_class=HTMLResponse)
def export_navigator_page(request: Request, session: Session = Depends(get_session)):
    exports = session.exec(select(ExportOpportunity).limit(20)).all()
    return templates.TemplateResponse("static_page.html", {"request": request, "title": "Export Navigator", "data": exports})

@router.get("/about", response_class=HTMLResponse)
def about(request: Request): return templates.TemplateResponse("about.html", {"request": request})

@router.get("/billing", response_class=HTMLResponse)
def billing(request: Request, user: User = Depends(get_current_user)): return templates.TemplateResponse("billing.html", {"request": request, "current_user": user, "plans": PRICING})

@router.get("/changelog", response_class=HTMLResponse)
def changelog(request: Request): return templates.TemplateResponse("changelog.html", {"request": request})

@router.get("/competitive", response_class=HTMLResponse)
def competitive(request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    last = session.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(1)).first()
    if last:
        stmt = select(Company).where(Company.sector == last.sector, Company.county == last.county).limit(20)
        companies = session.exec(stmt).all()
        sector, county = last.sector, last.county
    else: companies, sector, county = [], None, None
    return templates.TemplateResponse("competitive.html", {"request": request,"current_user": user,"companies": companies,"sector": sector,"county": county})

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request): return templates.TemplateResponse("contact.html", {"request": request})

@router.get("/location/counties", response_class=HTMLResponse)
def counties_page(request: Request, session: Session = Depends(get_session)):
    counties = session.exec(select(func.distinct(MarketMetric.county))).all()
    stats = session.exec(select(MarketMetric.county, func.sum(MarketMetric.avg_price_kes).label("market_size")).group_by(MarketMetric.county)).all()
    return templates.TemplateResponse("counties.html", {"request": request, "counties": [c[0] for c in counties], "stats": [dict(s._mapping) for s in stats]})

@router.get("/market/prices", response_class=HTMLResponse)
def prices_page(request: Request, session: Session = Depends(get_session)):
    prices = session.exec(select(MarketMetric).order_by(MarketMetric.created_at.desc()).limit(100)).all()
    return templates.TemplateResponse("prices.html", {"request": request, "prices": prices})

@router.get("/market/demand", response_class=HTMLResponse)
def demand_page(request: Request, session: Session = Depends(get_session)):
    demand = session.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
    return templates.TemplateResponse("demand.html", {"request": request, "demand": demand})

@router.get("/reports/funding", response_class=HTMLResponse)
def funding_page(request: Request, session: Session = Depends(get_session)):
    funders = session.exec(select(Company).where(or_(Company.sector.ilike("%Financial%"),Company.sector.ilike("%Banking%"),Company.sector.ilike("%Insurance%"),Company.sector.ilike("%SACCO%"))).limit(50)).all()
    return templates.TemplateResponse("funding.html", {"request": request, "funders": funders})

@router.get("/help", response_class=HTMLResponse)
def help(request: Request): return templates.TemplateResponse("help.html", {"request": request})

@router.get("/history", response_class=HTMLResponse)
def history(request: Request, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    stmt = select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(50)
    analyses = session.exec(stmt).all()
    return templates.TemplateResponse("history.html", {"request": request, "current_user": user, "analyses": analyses})

@router.get("/login", response_class=HTMLResponse)
def login(request: Request): return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
def signup(request: Request): return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/module_detail", response_class=HTMLResponse)
def module_detail(request: Request): return templates.TemplateResponse("module_detail.html", {"request": request})

@router.get("/kb/policy", response_class=HTMLResponse)
def policy_page(request: Request, session: Session = Depends(get_session)):
    policies = session.exec(select(NewsArticle).where(NewsArticle.category == "Policy").order_by(NewsArticle.published_at.desc()).limit(20)).all()
    return templates.TemplateResponse("policy.html", {"request": request, "policies": policies})

@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request): return templates.TemplateResponse("pricing.html", {"request": request, "plans": PRICING, "addons": ADDONS, "alc": ALC})

@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request): return templates.TemplateResponse("privacy.html", {"request": request})

@router.get("/risk", response_class=HTMLResponse)
def risk(request: Request): return templates.TemplateResponse("risk.html", {"request": request})

@router.get("/security", response_class=HTMLResponse)
def security(request: Request, user: User = Depends(get_current_user)): return templates.TemplateResponse("security.html", {"request": request, "current_user": user})

@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: User = Depends(get_current_user)): return templates.TemplateResponse("settings.html", {"request": request, "current_user": user})

@router.get("/static_page", response_class=HTMLResponse)
def static_page(request: Request): return templates.TemplateResponse("static_page.html", {"request": request})

@router.get("/stats", response_class=HTMLResponse)
def stats(request: Request, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    total = session.exec(select(func.count()).where(MarketMetric.user_id == user.id)).first()
    county_stmt = select(MarketMetric.county, func.count().label("c")).where(MarketMetric.user_id == user.id).group_by(MarketMetric.county).order_by(desc("c")).limit(5)
    top_counties = session.exec(county_stmt).all()
    return templates.TemplateResponse("stats.html", {"request": request,"current_user": user,"total_analyses": total,"credits_spent": total,"top_counties": top_counties})

@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request): return templates.TemplateResponse("terms.html", {"request": request})

@router.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request, session: Session = Depends(get_session)):
    posts = session.exec(select(SocialMention).order_by(SocialMention.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse("voice.html", {"request": request, "posts": posts})

@router.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, user: User = Depends(get_current_user)): return templates.TemplateResponse("wallet.html", {"request": request, "current_user": user})

@router.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request, user: User = Depends(get_current_user)): return templates.TemplateResponse("workspaces.html", {"request": request, "current_user": user})

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request): return templates.TemplateResponse("forgot.html", {"request": request})

@router.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, token: str): return templates.TemplateResponse("reset.html", {"request": request, "token": token})

@router.post("/chat")
async def chat(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    engine = LensEngineService(db)
    return await engine.chat(payload.get("message", ""), user.email)

@router.post("/auth/forgot-password")
def forgot_password(req: dict, session: Session = Depends(get_session)):
    email = req["email"]
    user = session.exec(select(User).where(User.email == email)).first()
    if not user: return {"message": "If an account exists, a reset link has been sent"}
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    session.add(user)
    session.commit()
    reset_link = f"https://evidlens.co.ke/auth/reset-password?token={token}"
    send_email(to=email, subject="Reset your EvidLens password", body=f"Click here to reset: {reset_link}. Link expires in 1 hour.")
    return {"message": "Password reset link sent to your email"}

@router.post("/auth/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.reset_token == token, User.reset_token_expires > datetime.utcnow())).first()
    if not user: return {"error": "Invalid token"}
    user.hashed_password = get_password_hash(password)
    user.reset_token = None
    user.reset_token_expires = None
    session.add(user)
    session.commit()
    return RedirectResponse("/login?success=Password reset", status_code=303)
