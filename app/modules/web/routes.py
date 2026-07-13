from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "result": None})

@router.get("/api/dashboard")
def api_dashboard():
    return JSONResponse({
        "trending": {"category": "ECONOMY", "headline": "Kenya inflation drops to 4.2% - Lowest in 18 months"},
        "lanes": [
            {"name": "Market Intel", "icon": "MI", "insights": "42", "growth": "+12%"},
            {"name": "Competitors", "icon": "CO", "insights": "28", "growth": "+8%"},
            {"name": "Pricing", "icon": "PR", "insights": "35", "growth": "+15%"},
            {"name": "Regulatory", "icon": "RG", "insights": "19", "growth": "+5%"},
            {"name": "Reports", "icon": "RP", "insights": "74", "growth": "+22%"},
            {"name": "AI Insights", "icon": "AI", "insights": "56", "growth": "+30%"}
        ]
    })

@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_msg = data.get("message", "")
    reply = f"I heard: '{user_msg}'. I'm Lens AI. Run an analysis above for market data."
    return JSONResponse({"reply": reply})

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
    result = login_user(db, email, password)
    if "error" in result: return templates.TemplateResponse("login.html", {"request": request, "error": result["error"]})
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/search-market", response_class=HTMLResponse)
def search_market_ui(request: Request, q: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_db)):
    try:
        result_data = search_market(db, q, sector, county)
        if not result_data: result_data = {"message": "No data found yet"}

        competitors = get_competitor_overview(db, sector, county)
        benchmark = get_sector_benchmark(sector) # FIXED: use sector directly
        ai_insights = generate_insights(q, result_data)

        result = {
            "q": q, "sector": sector, "county": county,
            "data": result_data,
            "competitors": competitors,
            "benchmark": benchmark,
            "ai": ai_insights
        }

    except Exception as e:
        result = {"error": str(e), "q": q, "sector": sector, "county": county}

    return templates.TemplateResponse("dashboard.html", {"request": request, "result": result})

@router.post("/pay-report")
def pay_report(request: Request, phone: str = Form(...), db: Session = Depends(get_db)):
    result = initiate_stk_push(db, phone_number=phone, amount=500, account_reference="report_001", user_id=1)
    return JSONResponse({"status": "success", "data": result}) # Return JSON for MPESA popup

@router.post("/download-report")
def download_report(q: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_db)):
    pdf_bytes = generate_report_pdf(db, q, sector, county)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=evidlens_report_{q}.pdf"})
