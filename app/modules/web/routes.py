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
    html_content = """
<!DOCTYPE html>
<html>
<head>
<title>EvidLens</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script>
<style>
body{background:#F5F7FA; font-family:-apple-system,BlinkMacSystemFont,sans-serif}
.card{background:white; border-radius:16px; padding:20px; box-shadow:0 1px 4px rgba(16,24,40,0.06)}
.teal-card{border-top:4px solid #14B8A6}
.lane-icon{background:linear-gradient(135deg, #0A1F44 0%, #14B8A6 100%)}
.trending{background:linear-gradient(135deg, #14B8A6 0%, #0D9488 100%)}
.footer{background:#0A1F44}
.footer-link{color:#CBD5E1}
.footer-link:hover{color:#14B8A6}
#chatWidget{position:fixed; bottom:24px; right:24px; z-index:9999}
#chatBtn{width:56px; height:56px; border-radius:50%; background:linear-gradient(135deg,#0A1F44,#14B8A6); color:white; border:none; font-size:24px; cursor:pointer}
#chatBox{width:380px; height:550px; background:white; border-radius:16px; display:none; flex-direction:column}
#chatHeader{background:#0A1F44; color:white; padding:14px 16px; font-weight:700}
#chatMessages{flex:1; overflow-y:auto; padding:16px; background:#F5F7FA}
.msg{margin-bottom:12px; padding:10px 12px; border-radius:12px; max-width:85%; font-size:14px}
.msg.user{background:#14B8A6; color:white; margin-left:auto}
.msg.bot{background:white; color:#0A1F44; border:1px solid #E2E8F0}
#chatInputBox{display:flex; padding:12px; border-top:1px solid #E2E8F0}
#chatInput{flex:1; border:1px solid #CBD5E1; border-radius:20px; padding:10px 14px; outline:none}
#chatSend{background:#F59E0B; color:white; border:none; border-radius:20px; padding:10px 18px; margin-left:8px; font-weight:600; cursor:pointer}
</style>
</head>
<body>
<header class="text-white px-6 py-4 sticky top-0" style="background:#0A1F44">
<div class="flex items-center gap-3 max-w-[1400px] mx-auto">
<img src="/static/logo.png?v=4" alt="EvidLens Logo" class="w-10 h-10 rounded-xl object-contain bg-white p-1">
<div><h1 class="font-bold text-2xl">Evid<span style="color:#14B8A6">Lens</span></h1></div>
</div>
</header>
<main class="px-4 py-6 max-w-[1400px] mx-auto">
<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
<div class="card teal-card"><p class="text-sm text-gray-500">Total Insights</p><p class="text-4xl font-bold" style="color:#0A1F44">0</p></div>
<div class="card teal-card"><p class="text-sm text-gray-500">Active Lanes</p><p class="text-4xl font-bold" style="color:#0A1F44">0</p></div>
<div class="card teal-card"><p class="text-sm text-gray-500">Reports</p><p class="text-4xl font-bold" style="color:#0A1F44">0</p></div>
<div class="card teal-card"><p class="text-sm text-gray-500">AI Queries</p><p class="text-4xl font-bold" style="color:#0A1F44">0</p></div>
</div>
<div class="mb-8"><h2 class="font-bold text-xl mb-4" style="color:#0A1F44">Trending Now</h2><div id="trendingCard" class="trending text-white p-6 rounded-2xl"><p id="trendingCategory">NO DATA</p><p id="trendingHeadline">Run an analysis to load real trends</p></div></div>
<div class="mb-8"><h2 class="font-bold text-xl mb-4" style="color:#0A1F44">Intelligence Lanes</h2><div class="grid grid-cols-3 gap-4" id="lanesGrid"></div></div>
<div class="card mb-6">
<h2 class="font-bold text-xl mb-3" style="color:#0A1F44">Quick Business Analysis</h2>
<form id="searchForm" class="space-y-3">
<input name="q" placeholder="e.g maize mill, retail, fintech" class="w-full p-3 border rounded-lg" required>
<div class="flex gap-3"><input name="sector" placeholder="Sector" class="w-1/2 p-3 border rounded-lg" required><input name="county" placeholder="County" class="w-1/2 p-3 border rounded-lg" required></div>
<button class="bg-[#F59E0B] text-white w-full p-3 rounded-lg font-bold">Analyze Market</button>
</form>
<div id="result" class="mt-4"></div>
</div>
</main>
<footer class="footer text-white pt-8 pb-8 mt-12">
<div class="max-w-[1400px] mx-auto px-6 grid-cols-4 gap-8">
<div><h3 style="color:#14B8A6">Legal</h3><a href="/privacy" class="footer-link">Privacy</a></div>
<div><h3 style="color:#14B8A6">Support</h3><a href="/contact" class="footer-link">Contact</a></div>
<div><h3 style="color:#14B8A6">Product</h3><a href="/pricing" class="footer-link">Pricing</a></div>
<div><h3 style="color:#14B8A6">Company</h3><a href="/about" class="footer-link">About</a></div>
</div>
</footer>
<div id="chatWidget"><div id="chatBox"><div id="chatHeader">Lens AI</div><div id="chatMessages"></div><div id="chatInputBox"><input id="chatInput"><button id="chatSend">Send</button></div></div><button id="chatBtn">💬</button></div>
<script>
let lastAnalysis = null;
async function loadDashboard(){ const res = await fetch('/api/dashboard'); const data = await res.json(); document.getElementById('trendingCategory').innerText = data.trending.category; document.getElementById('trendingHeadline').innerText = data.trending.headline; }
loadDashboard();
document.getElementById('searchForm').onsubmit = async (e) => { e.preventDefault(); const form = new FormData(e.target); lastAnalysis = Object.fromEntries(form); document.getElementById('result').innerHTML = 'Analyzing...'; const res = await fetch('/search-market', {method:'POST', body:form}); document.getElementById('result').innerHTML = await res.text(); }
document.getElementById('chatBtn').onclick = () => { let box = document.getElementById('chatBox'); box.style.display = box.style.display === 'flex'? 'none' : 'flex'; };
</script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

@router.get("/api/dashboard")
def api_dashboard():
    return JSONResponse({
        "trending": {"category": "NO DATA", "headline": "Run an analysis to load real trends"},
        "lanes": [
            {"name": "Market Intel", "icon": "MI", "insights": "0"},
            {"name": "Competitors", "icon": "CO", "insights": "0"},
            {"name": "Pricing", "icon": "PR", "insights": "0"},
            {"name": "Regulatory", "icon": "RG", "insights": "0"},
            {"name": "Reports", "icon": "RP", "insights": "0"},
            {"name": "AI Insights", "icon": "AI", "insights": "0"}
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
    result = login_user(db, email, password)
    if "error" in result: return templates.TemplateResponse("login.html", {"request": request, "error": result["error"]})
    return RedirectResponse(url="/dashboard", status_code=303)

@router.post("/search-market", response_class=HTMLResponse)
def search_market_ui(request: Request, q: str = Form(...), sector: str = Form(...), county: str = Form(...), db: Session = Depends(get_db)):
    try:
        result_data = search_market(db, q, sector, county)
        competitors = get_competitor_overview(db, sector, county)
        benchmark = get_sector_benchmark(sector)
        ai_insights = generate_insights(q, result_data)
        result = f"<div class='p-4 bg-green-50'><p><b>REAL DATA:</b> {q}</p><p>Benchmark: {benchmark}</p><p>AI: {ai_insights}</p><p>Competitors: {len(competitors)}</p><pre>{result_data}</pre></div>"
    except Exception as e:
        result = f"<div class='p-4 bg-red-50'><p><b>REAL ERROR:</b> {str(e)}</p><p>Fix this in service.py</p></div>"
    return HTMLResponse(content=result)

@router.get("/privacy")
def privacy(request: Request): return HTMLResponse("<body style='padding:40px'><h1>Privacy</h1><a href='/dashboard'>Back</a></body>")
@router.get("/terms")
def terms(request: Request): return HTMLResponse("<body style='padding:40px'><h1>Terms</h1><a href='/dashboard'>Back</a></body>")
@router.get("/contact")
def contact(request: Request): return HTMLResponse("<body style='padding:40px'><h1>Contact</h1><a href='/dashboard'>Back</a></body>")
@router.get("/pricing")
def pricing(request: Request): return HTMLResponse("<body style='padding:40px'><h1>Pricing</h1><a href='/dashboard'>Back</a></body>")
@router.get("/about")
def about(request: Request): return HTMLResponse("<body style='padding:40px'><h1>About</h1><a href='/dashboard'>Back</a></body>")
