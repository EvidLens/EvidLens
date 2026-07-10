from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.modules.db import get_db
from app.modules.auth.service import create_user, login_user, get_user_by_email
from app.modules.market_engine.service import search_market, get_competitor_overview
from app.modules.payments.service import initiate_stk_push
from app.modules.ai_insights.service import generate_insights
from app.modules.report_builder.service import generate_report_pdf
from app.modules.knowledge_base.service import get_sector_benchmark

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request): return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request): return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request): return templates.TemplateResponse("dashboard.html", {"request": request})

@router.post("/do-signup")
def do_signup(request: Request, email: str = Form(...), password: str = Form(...), full_name: str = Form(...), phone: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_db)):
    if get_user_by_email(db, email): return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
    class Req: pass
    req = Req(); req.email, req.password, req.full_name, req.phone, req.sector, req.county = email, password, full_name, phone, sector, county
    create_user(db, req)
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/do-login")
def do_login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    result = login_user(db, email, password)
    if "error" in result: return templates.TemplateResponse("login.html", {"request": request, "error": result["error"]})
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/search-market")
def search_market_ui(request: Request, q: str = Form(...), sector: str = Form(None), county: str = Form(None), db: Session = Depends(get_db)):
    result = search_market(db, q, sector, county)
    competitors = get_competitor_overview(db, result['sector'], county) if county else []
    benchmark = get_sector_benchmark(result['sector'])
    ai_insights = generate_insights(db, q, result)
    return templates.TemplateResponse("dashboard.html", {"request": request, "result": result, "competitors": competitors, "benchmark": benchmark, "ai": ai_insights})

@router.post("/pay-report")
def pay_report(request: Request, phone: str = Form(...), db: Session = Depends(get_db)):
    result = initiate_stk_push(db, phone_number=phone, amount=500, account_reference="report_001", user_id=1)
    return templates.TemplateResponse("dashboard.html", {"request": request, "payment": result})

@router.get("/download-report")
def download_report(request: Request, q: str):
    pdf = generate_report_pdf(q)
    return RedirectResponse(url=pdf)
