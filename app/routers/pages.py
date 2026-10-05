from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc, or_
from jinja2 import TemplateNotFound
import traceback

from app.core.db import get_session as get_db
from app.core.models import MarketMetric, Company, NewsArticle, SocialMention, ExportOpportunity
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# MAP old names -> your real files
TEMPLATE_ALIASES = {
    "demand.html": "market_demand.html",
    "prices.html": "market_prices.html",
    "counties.html": "location_counties.html",
    "risk.html": "market_risk.html",
    "voice.html": "voice.html",
    "voices.html": "voice.html",
}

def safe_template(request: Request, name: str, context: dict, fallback_title: str = ""):
    # always ensure request + current_user exists for base.html
    context["request"] = request
    context.setdefault("current_user", None)
    context.setdefault("user", context.get("current_user"))

    # try alias first
    try_names = [name]
    if name in TEMPLATE_ALIASES:
        try_names.append(TEMPLATE_ALIASES[name])
    # also try market_ prefix fallback
    if not name.startswith("market_") and not name.startswith("location_"):
        try_names.append(f"market_{name}")
        try_names.append(f"location_{name}")

    last_err = None
    for try_name in try_names:
        try:
            return templates.TemplateResponse(try_name, context)
        except TemplateNotFound as e:
            last_err = e
            continue
        except Exception as e:
            print(f"Template error {try_name}: {e}")
            traceback.print_exc()
            last_err = e
            continue

    print(f"TemplateNotFound: {name} tried {try_names} - {last_err}")
    title = fallback_title or name.replace('.html','').title()
    return HTMLResponse(f"""
    <html><head><title>{title}</title>
    <style>body{{font-family:Inter,sans-serif;padding:30px;background:#f8fafc}}.card{{background:white;padding:20px;border-radius:8px;border:1px solid #e2e8f0}}</style>
    </head><body>
    <a href="/">← Dashboard</a>
    <h1>{title}</h1>
    <div class="card"><p>Template <b>{name}</b> not found (tried {try_names}).</p><p>Data keys: {list(context.keys())}</p><p class="text-xs text-red-500">{last_err}</p></div>
    </body></html>
    """, status_code=200)

@router.get("/market/risk", response_class=HTMLResponse)
def risk_sentinel_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        news = db.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(100)).all()
        data = [n.model_dump() if hasattr(n,'model_dump') else {"title": getattr(n,'title','-')} for n in news]
    except Exception as e:
        print(f"risk query error: {e}")
        try: db.rollback()
        except: pass
        data = []
    return safe_template(request, "market_risk.html", {"request": request, "current_user": user, "risk_alerts": data, "risks": data, "risk": data}, "Risk Sentinel")

@router.get("/market/export", response_class=HTMLResponse)
def export_navigator_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        exports = db.exec(select(ExportOpportunity).limit(100)).all()
    except Exception as e:
        print(f"export query error: {e}")
        try: db.rollback()
        except: pass
        exports = []
    return safe_template(request, "market_export.html", {"request": request, "current_user": user, "title": "Export Navigator", "data": exports, "exports": exports}, "Export Navigator")

@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return safe_template(request, "about.html", {"request": request}, "About")

@router.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request, user: AuthUser = Depends(get_current_user)):
    return safe_template(request, "billing.html", {"request": request, "current_user": user}, "Billing")

@router.get("/changelog", response_class=HTMLResponse)
def changelog(request: Request):
    return safe_template(request, "changelog.html", {"request": request}, "Changelog")

@router.get("/competitive", response_class=HTMLResponse)
def competitive(request: Request, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        last = db.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(1)).first()
        if last:
            companies = db.exec(select(Company).where(Company.sector == last.sector, Company.county == last.county)).all()
            sector, county = last.sector, last.county
        else:
            companies = db.exec(select(Company)).all()
            sector, county = None, None
    except Exception as e:
        print(f"competitive error: {e}")
        try: db.rollback()
        except: pass
        try:
            companies = db.exec(select(Company)).all()
        except:
            companies = []
        sector, county = None, None

    return safe_template(request, "competitive.html", {
        "request": request,
        "current_user": user,
        "companies": companies,
        "competitors": companies,
        "count": len(companies),
        "sector": sector,
        "county": county
    }, "Competitive")

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return safe_template(request, "contact.html", {"request": request}, "Contact")

@router.get("/location/counties", response_class=HTMLResponse)
def counties_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        counties_raw = db.exec(select(func.distinct(MarketMetric.county))).all()
        counties = [c[0] if isinstance(c,(list,tuple)) else c for c in counties_raw if c]
        # also get company counts per county for richer UI
        county_counts = db.exec(select(Company.county, func.count().label("cnt")).group_by(Company.county)).all()
        count_map = {r[0]: r[1] for r in county_counts if r[0]}
    except Exception as e:
        print(f"counties query error: {e}")
        try: db.rollback()
        except: pass
        counties = []
        count_map = {}
    return safe_template(request, "location_counties.html", {"request": request, "current_user": user, "counties": counties, "count_map": count_map}, "Counties")

@router.get("/market/prices", response_class=HTMLResponse)
def prices_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        prices = db.exec(select(MarketMetric).order_by(MarketMetric.created_at.desc()).limit(500)).all()
    except Exception as e:
        print(f"prices query error: {e}")
        try: db.rollback()
        except: pass
        prices = []
    return safe_template(request, "market_prices.html", {"request": request, "current_user": user, "prices": prices}, "Price Oracle")

@router.get("/market/demand", response_class=HTMLResponse)
def demand_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        demand = db.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(500)).all()
    except Exception as e:
        print(f"demand query error: {e}")
        try: db.rollback()
        except: pass
        demand = []
    return safe_template(request, "market_demand.html", {"request": request, "current_user": user, "demand": demand, "voices": demand}, "Demand Radar")

@router.get("/reports/funding", response_class=HTMLResponse)
@router.get("/funding", response_class=HTMLResponse)
def funding_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        funders = db.exec(select(Company).where(or_(Company.sector.ilike("%Financial%"),Company.sector.ilike("%Banking%"),Company.sector.ilike("%Insurance%"),Company.sector.ilike("%SACCO%"))).all())
        counties_raw = db.exec(select(func.distinct(Company.county))).all()
        counties = [c[0] if isinstance(c,(list,tuple)) else c for c in counties_raw if c]
    except Exception as e:
        print(f"funding query error: {e}")
        try: db.rollback()
        except: pass
        funders, counties = [], []
    return safe_template(request, "reports_funding.html", {"request": request, "funders": funders, "companies": funders, "counties": counties, "current_user": user}, "Funding Radar")

@router.get("/help", response_class=HTMLResponse)
def help_page(request: Request):
    return safe_template(request, "help.html", {"request": request}, "Help")

@router.get("/history", response_class=HTMLResponse)
def history(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        analyses = db.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(100)).all()
    except Exception as e:
        print(f"history query error: {e}")
        try: db.rollback()
        except: pass
        analyses = []
    return safe_template(request, "history.html", {"request": request, "current_user": user, "analyses": analyses}, "History")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return safe_template(request, "login.html", {"request": request}, "Login")

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return safe_template(request, "signup.html", {"request": request}, "Signup")

@router.get("/kb/policy", response_class=HTMLResponse)
@router.get("/policy", response_class=HTMLResponse)
def policy_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        try:
            policies = db.exec(select(NewsArticle).where(NewsArticle.category == "policy").order_by(desc(NewsArticle.published_at)).limit(100)).all()
        except:
            policies = db.exec(select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(100)).all()
    except Exception as e:
        print(f"policy query error: {e}")
        try: db.rollback()
        except: pass
        policies = []
    return safe_template(request, "kb_policy.html", {"request": request, "policies": policies, "current_user": user, "new_count": len(policies)}, "Policy Watch")

@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return safe_template(request, "pricing.html", {"request": request}, "Pricing")

@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return safe_template(request, "privacy.html", {"request": request}, "Privacy")

@router.get("/risk", response_class=HTMLResponse)
def risk(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    return safe_template(request, "market_risk.html", {"request": request, "current_user": user}, "Risk")

@router.get("/security", response_class=HTMLResponse)
def security(request: Request, user: AuthUser = Depends(get_current_user)):
    return safe_template(request, "security.html", {"request": request, "current_user": user}, "Security")

@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: AuthUser = Depends(get_current_user)):
    return safe_template(request, "settings.html", {"request": request, "current_user": user}, "Settings")

@router.get("/stats", response_class=HTMLResponse)
def stats(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        total = db.exec(select(func.count()).select_from(MarketMetric).where(MarketMetric.user_id == user.id)).first() or 0
        top_counties = db.exec(select(MarketMetric.county, func.count().label("c")).where(MarketMetric.user_id == user.id).group_by(MarketMetric.county).order_by(desc("c")).limit(5)).all()
    except Exception as e:
        print(f"stats query error: {e}")
        try: db.rollback()
        except: pass
        total, top_counties = 0, []
    return safe_template(request, "stats.html", {"request": request,"current_user": user,"total_analyses": total,"credits_spent": total,"top_counties": top_counties}, "Stats")

@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return safe_template(request, "terms.html", {"request": request}, "Terms")

@router.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    try:
        posts = db.exec(select(SocialMention).order_by(SocialMention.created_at.desc()).limit(100)).all()
    except Exception as e:
        print(f"voice query error: {e}")
        try: db.rollback()
        except: pass
        posts = []
    return safe_template(request, "voice.html", {"request": request, "current_user": user, "posts": posts, "voices": posts, "voice": posts}, "Consumer Pulse")

@router.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, user: AuthUser = Depends(get_current_user)):
    return safe_template(request, "wallet.html", {"request": request, "current_user": user}, "Wallet")

@router.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request, user: AuthUser = Depends(get_current_user)):
    return safe_template(request, "workspaces.html", {"request": request, "current_user": user}, "Workspaces")

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request):
    return safe_template(request, "forgot.html", {"request": request}, "Forgot Password")

@router.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, token: str):
    return safe_template(request, "reset.html", {"request": request, "token": token}, "Reset Password")
