from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.modules.db import get_db
from app.modules.auth.service import create_user, login_user, get_user_by_email
from app.modules.market_engine.service import MarketEngineService
from app.modules.payments.service import initiate_stk_push
from app.modules.ai_insights.service import generate_insights
from app.modules.report_builder.service import generate_report_pdf
from app.modules.knowledge_base.service import get_sector_benchmark

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/api/dashboard")
def api_dashboard():
    return JSONResponse({
        "trending": {"category": "NO DATA", "headline": "Run an analysis to load real trends"},
        "lanes": [
            {"name": "Market Intel", "icon": "MI", "insights": "0", "growth": "0%"},
            {"name": "Competitors", "icon": "CO", "insights": "0", "growth": "0%"},
            {"name": "Pricing", "icon": "PR", "insights": "0", "growth": "0%"},
            {"name": "Regulatory", "icon": "RG", "insights": "0", "growth": "0%"},
            {"name": "Reports", "icon": "RP", "insights": "0", "growth": "0%"},
            {"name": "AI Insights", "icon": "AI", "insights": "0", "growth": "0%"}
        ]
    })

@router.post("/chat")
async def chat(request: Request):
    return JSONResponse({"reply": "Run a real analysis first, then I can answer with data."})

@router.post("/do-signup")
def do_signup(request: Request, email: str = Form(...), password: str = Form(...), full_name: str = Form(...), phone: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_db)):
    if get_user_by_email(db, email): return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
    class Req: pass
    req = Req()
    req.email, req.password, req.full_name, req.phone, req.sector, req.county = email, password, full_name, phone, sector, county
    create_user(db, req)
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/do-login")
def do_login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    result = login_user(next(db), email, password)
    if "error" in result: return templates.TemplateResponse("login.html", {"request": request, "error": result["error"]})
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/search-market", response_class=HTMLResponse)
def search_market_ui(request: Request, q: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_db)):
    try:
        result_data = search_market(db, q, sector, county)
        competitors = get_competitor_overview(db, sector, county)
        benchmark = get_sector_benchmark(sector)
        ai_insights = generate_insights(q, result_data)
        result = f"<div class='p-4 bg-green-50 rounded-lg'><p><b>REAL:</b> {q}</p><p>Benchmark: {benchmark}</p><p>AI: {ai_insights}</p><p>Competitors: {len(competitors)}</p></div>"
    except Exception as e:
        result = f"<div class='p-4 bg-red-50 rounded-lg'><p><b>ERROR:</b> {str(e)}</p></div>"
    return HTMLResponse(content=result)

@router.get("/privacy")
def privacy(request: Request): return templates.TemplateResponse("privacy.html", {"request": request})
@router.get("/terms")
def terms(request: Request): return templates.TemplateResponse("terms.html", {"request": request})
@router.get("/contact")
def contact(request: Request): return templates.TemplateResponse("contact.html", {"request": request})
@router.get("/pricing")
def pricing(request: Request): return templates.TemplateResponse("pricing.html", {"request": request})
@router.get("/about")
def about(request: Request): return templates.TemplateResponse("about.html", {"request": request})
