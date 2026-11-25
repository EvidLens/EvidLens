from fastapi import APIRouter
from fastapi import Request
from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from sqlmodel import select
from sqlmodel import func
from sqlmodel import desc
from sqlmodel import or_
from jinja2 import TemplateNotFound
import traceback
import markdown, bleach
from app.core.db import get_session as get_db
from app.core.models import MarketMetric
from app.core.models import Company
from app.core.models import NewsArticle
from app.core.models import SocialMention
from app.core.models import ExportOpportunity
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
TEMPLATE_ALIASES = {"demand.html": "market_demand.html", "prices.html": "market_prices.html", "counties.html": "location_counties.html", "risk.html": "market_risk.html", "voice.html": "voice.html", "voices.html": "voice.html"}

PUBLIC_PAGES = {"/login", "/signup", "/forgot-password", "/reset-password", "/privacy", "/terms", "/pricing", "/about", "/contact", "/help", "/changelog"}

# --- Static pages (about / terms / privacy / help) rendered via static_page.html ---
ALLOWED_TAGS = ["p","h1","h2","h3","h4","ul","ol","li","a","strong","em","br","hr","blockquote","code"]
ALLOWED_ATTRS = {"a": ["href", "title"]}

PAGES = {
  "about": {"title": "About EvidLens", "subtitle": "Real market intelligence for Kenyan businesses.", "updated_at": "2026-11-25", "md": """
## What EvidLens does
EvidLens helps Kenyan businesses make decisions with real data, not guesswork.
- **Market Engine** - prices, demand, and competition across 47 counties
- **Policy Watch** - KRA, KEBS, CBK and county policy changes that affect you
- **Funding Radar** - banks, SACCOs, grants, and investors
- **Ask Lens** - ask a business question in plain English, get a sourced answer
## Who it is for
Small traders, agribusinesses, retailers, manufacturers, and service businesses operating in Kenya.
## What we do not do
We do not lend money, guarantee funding approval, or give legal / tax advice. Always verify terms with the lender or a professional before you commit.
## Contact
Email [support@evidlens.co.ke](mailto:support@evidlens.co.ke)
"""},
  "terms": {"title": "Terms of Service", "subtitle": "Please read these before using EvidLens.", "updated_at": "2026-11-25", "md": """
## 1. The Service
EvidLens provides market, policy, and funding information for general business use.
## 2. No guarantee
Data comes from public sources, partners, and user inputs. It may be incomplete or out of date. You are responsible for verifying prices, policy, and lender terms before acting on them.
## 3. Your account
You are responsible for keeping your password safe. Do not share your account. Tell us immediately if you think it has been compromised.
## 4. Fair use
Do not scrape, resell, or abuse the Service, or try to access other users' data.
## 5. Changes
We may update these Terms. The date at the bottom of this page shows the latest version.
## 6. Contact
Questions: [support@evidlens.co.ke](mailto:support@evidlens.co.ke)
"""},
  "privacy": {"title": "Privacy Policy", "subtitle": "What we collect, why, and what we never sell.", "updated_at": "2026-11-25", "md": """
## What we collect
- Account info you give us: name, email, phone, county, sector
- Questions you ask Lens, and reports you generate
- Basic usage logs to keep the Service running and secure
## What we do NOT do
We do not sell your personal data. We do not share your reports with other users.
## How we use it
To run your account, show you relevant market data, improve the Service, and prevent abuse.
## Your choices
You can update your profile in Settings. To delete your account, email [support@evidlens.co.ke](mailto:support@evidlens.co.ke) from your registered email.
## Contact
Privacy questions: [support@evidlens.co.ke](mailto:support@evidlens.co.ke)
"""},
  "help": {"title": "Help", "subtitle": "Get unstuck fast.", "updated_at": "2026-11-25", "md": """
## Getting started
1. Create an account and set your county and sector in Settings
2. Go to the Dashboard to see your market snapshot
3. Use Ask Lens for any question, e.g. "What is the price of maize in Nyeri this week?"
## Reports
Go to My Reports > Generate New Report, enter what to analyze, then download the PDF when status shows READY.
## Funding
Go to Funding Radar, filter by sector and county, and always verify interest, fees, and eligibility directly with the lender before sharing documents or paying fees.
## Still stuck?
Email [support@evidlens.co.ke](mailto:support@evidlens.co.ke) with your email, what page you were on, and a screenshot if you can.
"""},
}

def render_md(md_text: str) -> str:
    html = markdown.markdown(md_text or "", extensions=["extra"])
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

def static_page(request: Request, slug: str):
    page = PAGES[slug]
    return safe_template(request, "static_page.html", {"request": request, "title": page["title"], "subtitle": page.get("subtitle"), "content_html": render_md(page["md"]), "updated_at": page.get("updated_at")}, page["title"])

def _needs_login(request: Request, user):
    if user is not None:
        return None
    if not request.cookies.get("user_id"):
        return RedirectResponse(url="/login", status_code=302)
    return None

def safe_template(request: Request, name: str, context: dict, fallback_title: str = ""):
    context["request"] = request
    context.setdefault("current_user", None)
    context.setdefault("user", context.get("current_user"))
    try_names = [name]
    if name in TEMPLATE_ALIASES:
        try_names.append(TEMPLATE_ALIASES[name])
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
    title = fallback_title or name.replace('.html', '').title()
    return HTMLResponse(f"""<html><head><title>{title}</title><style>body{{font-family:Inter,sans-serif;padding:30px;background:#f8fafc}}.card{{background:white;padding:20px;border-radius:8px;border:1px solid #e2e8f0}}</style></head><body><a href="/">← Dashboard</a><h1>{title}</h1><div class="card"><p>Template <b>{name}</b> not found (tried {try_names}).</p><p>Data keys: {list(context.keys())}</p><p class="text-xs text-red-500">{last_err}</p></div></body></html>""", status_code=200)

@router.get("/market/risk", response_class=HTMLResponse)
def risk_sentinel_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        news = list(db.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(100)))
        data = [n.model_dump() if hasattr(n, 'model_dump') else {"title": getattr(n, 'title', '-')} for n in news]
    except Exception as e:
        print(f"risk query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        data = []
    return safe_template(request, "market_risk.html", {"request": request, "current_user": user, "risk_alerts": data, "risks": data, "risk": data}, "Risk Sentinel")

@router.get("/market/export", response_class=HTMLResponse)
def export_navigator_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        exports = list(db.exec(select(ExportOpportunity).limit(100)))
    except Exception as e:
        print(f"export query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        exports = []
    return safe_template(request, "market_export.html", {"request": request, "current_user": user, "title": "Export Navigator", "data": exports, "exports": exports}, "Export Navigator")

@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return static_page(request, "about")

@router.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    return safe_template(request, "billing.html", {"request": request, "current_user": user}, "Billing")

@router.get("/changelog", response_class=HTMLResponse)
def changelog(request: Request):
    return safe_template(request, "changelog.html", {"request": request}, "Changelog")

@router.get("/competitive", response_class=HTMLResponse)
def competitive(request: Request, user: AuthUser = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        last = db.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(1)).first() if user else None
        if last:
            companies = list(db.exec(select(Company).where(Company.sector == last.sector, Company.county == last.county)))
            sector, county = last.sector, last.county
        else:
            companies = list(db.exec(select(Company)))
            sector, county = None, None
    except Exception as e:
        print(f"competitive error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        try:
            companies = list(db.exec(select(Company)))
        except Exception:
            companies = []
        sector, county = None, None
    return safe_template(request, "competitive.html", {"request": request, "current_user": user, "companies": companies, "competitors": companies, "count": len(companies), "sector": sector, "county": county}, "Competitive")

@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return safe_template(request, "contact.html", {"request": request}, "Contact")

@router.get("/location/counties", response_class=HTMLResponse)
def counties_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        counties_raw = list(db.exec(select(func.distinct(MarketMetric.county))))
        counties = [c[0] if isinstance(c, (list, tuple)) else c for c in counties_raw if c]
        county_counts = list(db.exec(select(Company.county, func.count().label("cnt")).group_by(Company.county)))
        count_map = {r[0]: r[1] for r in county_counts if r[0]}
    except Exception as e:
        print(f"counties query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        counties = []
        count_map = {}
    return safe_template(request, "location_counties.html", {"request": request, "current_user": user, "counties": counties, "count_map": count_map}, "Counties")

@router.get("/market/prices", response_class=HTMLResponse)
def prices_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        prices = list(db.exec(select(MarketMetric).order_by(MarketMetric.created_at.desc()).limit(500)))
    except Exception as e:
        print(f"prices query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        prices = []
    return safe_template(request, "market_prices.html", {"request": request, "current_user": user, "prices": prices}, "Price Oracle")

@router.get("/market/demand", response_class=HTMLResponse)
def demand_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        demand = list(db.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(500)))
    except Exception as e:
        print(f"demand query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        demand = []
    return safe_template(request, "market_demand.html", {"request": request, "current_user": user, "demand": demand, "voices": demand}, "Demand Radar")

@router.get("/reports/funding", response_class=HTMLResponse)
@router.get("/funding", response_class=HTMLResponse)
def funding_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        funders = list(db.exec(select(Company).where(or_(Company.sector.ilike("%Financial%"), Company.sector.ilike("%Banking%"), Company.sector.ilike("%Insurance%"), Company.sector.ilike("%SACCO%")))))
        counties_raw = list(db.exec(select(func.distinct(Company.county))))
        counties = [c[0] if isinstance(c, (list, tuple)) else c for c in counties_raw if c]
    except Exception as e:
        print(f"funding query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        funders, counties = [], []
    return safe_template(request, "reports_funding.html", {"request": request, "funders": funders, "companies": funders, "counties": counties, "current_user": user}, "Funding Radar")

@router.get("/help", response_class=HTMLResponse)
def help_page(request: Request):
    return static_page(request, "help")

@router.get("/history", response_class=HTMLResponse)
def history(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        analyses = list(db.exec(select(MarketMetric).where(MarketMetric.user_id == user.id).order_by(desc(MarketMetric.timestamp)).limit(100))) if user else []
    except Exception as e:
        print(f"history query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        analyses = []
    return safe_template(request, "history.html", {"request": request, "current_user": user, "analyses": analyses}, "History")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    if user is not None:
        return RedirectResponse(url="/", status_code=302)
    return safe_template(request, "login.html", {"request": request}, "Login")

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    if user is not None:
        return RedirectResponse(url="/", status_code=302)
    return safe_template(request, "signup.html", {"request": request}, "Signup")

@router.get("/kb/policy", response_class=HTMLResponse)
@router.get("/policy", response_class=HTMLResponse)
def policy_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        try:
            policies = list(db.exec(select(NewsArticle).where(NewsArticle.category == "policy").order_by(desc(NewsArticle.published_at)).limit(100)))
        except Exception:
            policies = list(db.exec(select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(100)))
    except Exception as e:
        print(f"policy query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        policies = []
    return safe_template(request, "kb_policy.html", {"request": request, "policies": policies, "current_user": user, "new_count": len(policies)}, "Policy Watch")

@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return safe_template(request, "pricing.html", {"request": request}, "Pricing")

@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return static_page(request, "privacy")

@router.get("/risk", response_class=HTMLResponse)
def risk(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    return safe_template(request, "market_risk.html", {"request": request, "current_user": user}, "Risk")

@router.get("/security", response_class=HTMLResponse)
def security(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    return safe_template(request, "security.html", {"request": request, "current_user": user}, "Security")

@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    return safe_template(request, "settings.html", {"request": request, "current_user": user}, "Settings")

@router.get("/stats", response_class=HTMLResponse)
def stats(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        total = db.exec(select(func.count()).select_from(MarketMetric).where(MarketMetric.user_id == user.id)).first() or 0 if user else 0
        top_counties = list(db.exec(select(MarketMetric.county, func.count().label("c")).where(MarketMetric.user_id == user.id).group_by(MarketMetric.county).order_by(desc("c")).limit(5))) if user else []
    except Exception as e:
        print(f"stats query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        total, top_counties = 0, []
    return safe_template(request, "stats.html", {"request": request, "current_user": user, "total_analyses": total, "credits_spent": total, "top_counties": top_counties}, "Stats")

@router.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return static_page(request, "terms")

@router.get("/voice", response_class=HTMLResponse)
def voice_page(request: Request, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    try:
        posts = list(db.exec(select(SocialMention).order_by(SocialMention.created_at.desc()).limit(100)))
    except Exception as e:
        print(f"voice query error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        posts = []
    return safe_template(request, "voice.html", {"request": request, "current_user": user, "posts": posts, "voices": posts, "voice": posts}, "Consumer Pulse")

@router.get("/wallet", response_class=HTMLResponse)
def wallet(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    return safe_template(request, "wallet.html", {"request": request, "current_user": user}, "Wallet")

@router.get("/workspaces", response_class=HTMLResponse)
def workspaces(request: Request, user: AuthUser = Depends(get_current_user_optional)):
    redir = _needs_login(request, user)
    if redir is not None:
        return redir
    return safe_template(request, "workspaces.html", {"request": request, "current_user": user}, "Workspaces")

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request):
    return safe_template(request, "forgot.html", {"request": request}, "Forgot Password")

@router.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, token: str = ""):
    return safe_template(request, "reset.html", {"request": request, "token": token}, "Reset Password")
