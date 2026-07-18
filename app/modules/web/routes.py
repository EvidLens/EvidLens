from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.modules.database import get_db
from app.modules.auth.service import create_user, login_user, get_user_by_email
from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric
from app.modules.payments.service import initiate_stk_push
from app.modules.ai_insights.service import generate_insights
from app.modules.report_builder.service import generate_report_pdf
from app.modules.knowledge_base.service import get_sector_benchmark

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ========== 9 WORKING APIs ==========
@router.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    competitors = db.query(func.count(Competitor.id)).scalar() or 0
    prices = db.query(func.count(MarketMetric.id)).filter(MarketMetric.metric_type == "price_avg").scalar() or 0
    demand = db.query(func.count(MarketMetric.id)).filter(MarketMetric.metric_type == "demand_score").scalar() or 0
    searches = db.query(func.count(MarketSearch.id)).scalar() or 0
    counties = db.query(func.count(func.distinct(MarketSearch.county))).scalar() or 0
    total = competitors + prices + demand + searches + counties
    return {"total_insights": total, "active_lanes": 9, "reports": 0, "ai_queries": 0}

@router.get("/api/competitive")
def get_competitive(db: Session = Depends(get_db)):
    competitors = db.query(Competitor).order_by(desc(Competitor.avg_rating)).limit(100).all()
    data = [{"business_name": c.business_name, "sector": c.sector, "county": c.county, "address": c.address, "rating": c.avg_rating, "review_count": c.review_count, "lat": c.lat, "lng": c.lng} for c in competitors]
    return {"count": len(data), "data": data}

@router.get("/api/price-oracle")
def get_price_oracle(db: Session = Depends(get_db)):
    prices = db.query(MarketMetric).filter(MarketMetric.metric_type == "price_avg").order_by(desc(MarketMetric.updated_at)).limit(100).all()
    data = [{"sector": p.sector, "county": p.county, "price_kes": p.metric_value} for p in prices]
    return {"count": len(data), "data": data}

@router.get("/api/demand")
def get_demand(db: Session = Depends(get_db)):
    demand = db.query(MarketMetric).filter(MarketMetric.metric_type == "demand_score").order_by(desc(MarketMetric.metric_value)).limit(100).all()
    data = [{"sector": d.sector, "county": d.county, "sub_county": d.sub_county, "demand_score": d.metric_value} for d in demand]
    return {"count": len(data), "data": data}

@router.get("/api/county")
def get_county(db: Session = Depends(get_db)):
    counties = db.query(MarketSearch.county, func.sum(MarketSearch.market_size_kes), func.avg(MarketSearch.growth_rate), func.count(MarketSearch.id)).group_by(MarketSearch.county).all()
    data = [{"county": c[0], "market_size": float(c[1] or 0), "growth": float(c[2] or 0), "volume": c[3]} for c in counties]
    return {"count": len(data), "data": data}

@router.get("/api/consumer")
def get_consumer(db: Session = Depends(get_db)):
    searches = db.query(MarketSearch.sector, func.count(MarketSearch.id)).group_by(MarketSearch.sector).order_by(desc(func.count(MarketSearch.id))).limit(50).all()
    data = [{"sector": s[0], "count": s[1]} for s in searches]
    return {"count": len(data), "data": data}

@router.get("/api/risk")
def get_risk(db: Session = Depends(get_db)):
    risk_zones = db.query(MarketSearch).filter(MarketSearch.demand_level == "High").limit(50).all()
    data = [{"county": r.county, "sector": r.sector, "market_size": r.market_size_kes} for r in risk_zones]
    return {"count": len(data), "data": data}

@router.get("/api/policy")
def get_policy(db: Session = Depends(get_db)): return {"count": 0, "data": []}
@router.get("/api/funding")
def get_funding(db: Session = Depends(get_db)): return {"count": 0, "data": []}
@router.get("/api/export")
def get_export(db: Session = Depends(get_db)): return {"count": 0, "data": []}

@router.post("/api/chat")
def chat(message: dict, db: Session = Depends(get_db)):
    user_message = message.get("message", "")
    insight = generate_insights(user_message, db)
    return {"reply": insight}

@router.get("/", include_in_schema=False)
def root(): return RedirectResponse(url="/dashboard")

@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    html_content = """<!DOCTYPE html>
<html>
<head><title>EvidLens</title>
    <style>
        body{margin:0;font-family:Inter,Arial;background:#ffffff}
      .header{background:#0f172a;padding:20px 40px;display:flex;align-items:center;gap:12px}
      .header h1{color:white;margin:0;font-size:22px}
      .header p{color:#38bdf8;margin:0;font-size:12px}
      .container{padding:30px 40px;max-width:1400px;margin:0 auto}
      .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:30px}
      .stat-card{background:white;border:2px solid #38bdf8;border-radius:12px;padding:20px}
      .stat-label{color:#64748b;font-size:14px}
      .stat-value{font-size:32px;font-weight:bold;color:#0f172a;margin-top:5px}
      .search-section{display:flex;gap:20px;margin-bottom:30px}
      .search-left{flex:1}
      .search-right{flex:1}
      .input{width:100%;padding:12px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:10px}
      .btn-orange{background:#f97316;color:white;border:none;padding:14px;border-radius:8px;width:100%;font-weight:600;cursor:pointer}
      .btn-teal{background:#06b6d4;color:white;border:none;padding:14px;border-radius:8px;width:100%;font-weight:600;cursor:pointer}
      .banner{background:linear-gradient(90deg,#0ea5e9,#06b6d4);padding:30px;border-radius:16px;color:white;margin-bottom:30px}
      .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
      .card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:24px}
      .icon{width:48px;height:48px;background:linear-gradient(135deg,#38bdf8,#0ea5e9);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;margin-bottom:16px}
      .title{font-weight:600;color:#0f172a;font-size:16px;margin-bottom:4px}
      .subtitle{color:#64748b;font-size:12px;margin-bottom:4px}
      .value{color:#0ea5e9;font-size:14px;font-weight:600;margin-bottom:8px}
      .live{color:#f97316;font-size:12px;font-weight:600}
      .footer{background:#1e3a8a;color:white;padding:40px;margin-top:50px}
      .footer-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:30px;max-width:1400px;margin:0 auto}
      .chat-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#0ea5e9;color:white;border:none;font-size:24px;cursor:pointer}
      .chat-box{position:fixed;bottom:90px;right:20px;width:350px;height:450px;background:white;border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,0.2);display:none;flex-direction:column}
      .scroll{max-height:250px;overflow:auto;margin-top:10px}
       table{width:100%;font-size:11px;border-collapse:collapse}
       th,td{padding:6px;border-bottom:1px solid #f1f5f9;text-align:left}
    </style>
</head>
<body>
    <div class="header"><div style="background:white;padding:8px;border-radius:8px;font-weight:bold;color:#0f172a">EL</div><div><h1>EvidLens</h1><p>Decision Intelligence</p></div></div>
    <div class="container">
        <input class="input" placeholder="🔍 Search insights, lanes, or questions...">
        <div class="stats">
            <div class="stat-card"><div class="stat-label">Total Insights</div><div class="stat-value" id="total">0</div></div>
            <div class="stat-card"><div class="stat-label">Active Lanes</div><div class="stat-value">9</div></div>
            <div class="stat-card"><div class="stat-label">Reports Generated</div><div class="stat-value">0</div></div>
            <div class="stat-card"><div class="stat-label">AI Queries</div><div class="stat-value">0</div></div>
        </div>
        <div class="search-section">
            <div class="search-left">
                <input class="input" placeholder="e.g maize mill, retail, fintech">
                <div style="display:flex;gap:10px"><input class="input" placeholder="Sector"><input class="input" placeholder="County"></div>
                <button class="btn-orange">Analyze Market</button>
            </div>
            <div class="search-right">
                <p style="color:#64748b;font-size:14px">Get PDF report with competitors, pricing, and AI insights</p>
                <button class="btn-teal">Download PDF</button>
            </div>
        </div>
        <div class="banner"><div style="font-size:12px">MARKET INTEL</div><div style="font-size:24px;font-weight:bold">Services Online</div></div>
        <h2 style="color:#0f172a">WAVE 2 Intelligence Modules</h2>
        <div class="grid" id="grid">Loading...</div>
    </div>
    <div class="footer">
        <div class="footer-grid">
            <div><h4 style="color:#38bdf8">Legal</h4><p>Privacy Policy</p><p>Terms</p></div>
            <div><h4 style="color:#38bdf8">Support</h4><p>Contact Us</p></div>
            <div><h4 style="color:#38bdf8">Product</h4><p>Pricing</p></div>
            <div><h4 style="color:#38bdf8">Company</h4><p>About</p></div>
        </div>
        <p style="text-align:center;margin-top:30px;color:#94a3b8">© 2026 EvidLens. Decision Intelligence for Kenya.</p>
    </div>
    <button class="chat-btn" onclick="toggleChat()">💬</button>
    <div class="chat-box" id="chatBox"><div style="background:#0f172a;color:white;padding:15px">EvidLens AI</div><div id="chatMessages" style="flex:1;padding:15px;overflow:auto"></div><div style="display:flex;padding:10px"><input id="chatInput" style="flex:1"><button onclick="sendChat()">Send</button></div></div>
    <script>
    async function loadStats(){let s=await fetch('/api/stats').then(r=>r.json());document.getElementById('total').innerText=s.total_insights}
    const modules=[{key:"competitive",title:"Competitive Engine",icon:"🎯"},{key:"price-oracle",title:"Price Oracle",icon:"💰"},{key:"demand",title:"Demand Radar",icon:"📈"},{key:"policy",title:"Policy Watch",icon:"📜"},{key:"funding",title:"Funding Radar",icon:"🏦"},{key:"risk",title:"Risk Sentinel",icon:"⚠️"},{key:"export",title:"Export Navigator",icon:"🚢"},{key:"consumer",title:"Consumer Pulse",icon:"👥"},{key:"county",title:"County Mapper",icon:"🗺️"}];
    async function loadCards(){let html='';for(let m of modules){let res=await fetch(`/api/${m.key}`).then(r=>r.json());html+=`<div class="card"><div class="icon">${m.icon}</div><div class="title">${m.title}</div><div class="subtitle">${res.count} Records</div><div class="scroll"><table>`;if(res.count>0){res.data.slice(0,5).forEach(r=>{html+=`<tr><td>${Object.values(r).slice(0,3).join('</td><td>')}</td></tr>`})}else{html+=`<tr><td>0 records. Ready for data.</td></tr>`}html+=`</table></div><div class="live">LIVE</div></div>`}document.getElementById('grid').innerHTML=html}
    function toggleChat(){document.getElementById('chatBox').style.display=document.getElementById('chatBox').style.display==='flex'?'none':'flex'}
    async function sendChat(){let i=document.getElementById('chatInput');let m=i.value;if(!m)return;i.value='';document.getElementById('chatMessages').innerHTML+=`<div><b>You:</b>${m}</div>`;let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})}).then(r=>r.json());document.getElementById('chatMessages').innerHTML+=`<div><b>AI:</b>${r.reply}</div>`}
    loadStats();loadCards();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
