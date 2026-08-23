from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc, or_
from datetime import datetime, timedelta
import secrets

from app.core.db import get_session as get_db
from app.core.models import MarketMetric, Company, NewsArticle, SocialMention, ExportOpportunity
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

@router.get("/market/risk", response_class=HTMLResponse)
def risk_sentinel_page(request: Request, db: Session = Depends(get_db)):
    news = db.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(10)).all()
    return templates.TemplateResponse("risk.html", {"request": request, "risk_alerts": [n.model_dump() for n in news]})

@router.get("/market/export", response_class=HTMLResponse)
def export_navigator_page(request: Request, db: Session = Depends(get_db)):
    exports = db.exec(select(ExportOpportunity).limit(20)).all()
    return templates.TemplateResponse("static_page.html", {"request": request, "title": "Export Navigator", "data": exports})

@router.get("/about", response_class=HTMLResponse)
def about(request: Request): return templates.TemplateResponse("about.html", {"request": request})

@router.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("billing.html", {"request": request, "current_user": user})

@router.get("/changelog", response_class=HTMLResponse)
def changelog(request: Request): return templates.TemplateResponse("changelog.html", {"request": request})

@router.get("/competitive", response_class=HTMLResponse)
def competitive(request: Request, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    last = db.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(1)).first()
    if last:
        companies = db.exec(select(Company).where(Company.sector == last.sector, Company.county == last.county).limit(20)).all()
        sector, county = last.sector, last.county
    else: companies, sector, county = [], None, None
    return templates.TemplateResponse("competitive.html", {"request": request,"current_user": user,"companies": companies,"sector": sector,"county": county})

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request): return templates.TemplateResponse("contact.html", {"request": request})

@router.get("/location/counties", response_class=HTMLResponse)
def counties_page(request: Request, db: Session = Depends(get_db)):
    counties = db.exec(select(func.distinct(MarketMetric.county))).all()
    return templates.TemplateResponse("counties.html", {"request": request, "counties": [c[0] if isinstance(c,(list,tuple)) else c for c in counties]})

@router.get("/market/prices", response_class=HTMLResponse)
def prices_page(request: Request, db: Session = Depends(get_db)):
    prices = db.exec(select(MarketMetric).order_by(MarketMetric.created_at.desc()).limit(100)).all()
    return templates.TemplateResponse("prices.html", {"request": request, "prices": prices})

@router.get("/market/demand", response_class=HTMLResponse)
def demand_page(request: Request, db: Session = Depends(get_db)):
    demand = db.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
    return templates.TemplateResponse("demand.html", {"request": request, "demand": demand})

@router.get("/reports/funding", response_class=HTMLResponse)
def funding_page(request: Request, db: Session = Depends(get_db)):
    funders = db.exec(select(Company).where(or_(Company.sector.ilike("%Financial%"),Company.sector.ilike("%Banking%"),Company.sector.ilike("%Insurance%"),Company.sector.ilike("%SACCO%"))).limit(50)).all()
    return templates.TemplateResponse("funding.html", {"request": request, "funders": funders})

@router.get("/help", response_class=HTMLResponse)
def help_page(request: Request): return templates.TemplateResponse("help.html", {"request": request})

@router.get("/history", response_class=HTMLResponse)
def history(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    analyses = db.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(50)).all()
    return templates.TemplateResponse("history.html", {"request": request, "current_user": user, "analyses": analyses})

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request): return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/kb/policy", response_class=HTMLResponse)
def policy_page(request: Request, db: Session = Depends(get_db)):
    policies = db.exec(select(NewsArticle).where(NewsArticle.category == "Policy").order_by(NewsArticle.published_at.desc()).limit(20)).all()
    return templates.TemplateResponse("policy.html", {"request": request, "policies": policies})

@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request): return templates.TemplateResponse("pricing.html", {"request": request})

@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request): return templates.TemplateResponse("privacy.html", {"request": request})

@router.get("/risk", response_class=HTMLResponse)
def risk(request: Request): return templates.TemplateResponse("risk.html", {"request": request})

@router.get("/security", response_class=HTMLResponse)
def security(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("security.html", {"request": request, "current_user": user})

@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("settings.html", {"request": request, "current_user": user})

@router.get("/stats", response_class=HTMLResponse)
def stats(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    total = db.exec(select(func.count()).select_from(MarketMetric).where(MarketMetric.user_id == user.id)).first() or 0
    top_counties = db.exec(select(MarketMetric.county, func.count().label("c")).where(MarketMetric.user_id == user.id).group_by(MarketMetric.county).order_by(desc("c")).limit(5)).all()
    return templates.TemplateResponse("stats.html", {"request": request,"current_user": user,"total_analyses": total,"credits_spent": total,"top_counties": top_counties})

@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request): return templates.TemplateResponse("terms.html", {"request": request})

@router.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request, db: Session = Depends(get_db)):
    posts = db.exec(select(SocialMention).order_by(SocialMention.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse("voice.html", {"request": request, "posts": posts})

@router.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("wallet.html", {"request": request, "current_user": user})

@router.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request, user: AuthUser = Depends(get_current_user)): return templates.TemplateResponse("workspaces.html", {"request": request, "current_user": user})

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request): return templates.TemplateResponse("forgot.html", {"request": request})

@router.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, token: str): return templates.TemplateResponse("reset.html", {"request": request, "token": token})
