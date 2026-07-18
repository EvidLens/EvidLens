from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
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

# ========== 9 ENDLESS REAL APIs ==========
@router.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    db = next(db)
    total = db.query(func.count(Competitor.id)).scalar() + db.query(func.count(MarketMetric.id)).scalar() + db.query(func.count(MarketSearch.id)).scalar()
    return {"total_insights": total, "active_lanes": 9, "reports": 0, "ai_queries": 0}

@router.get("/api/competitive")
def get_competitive(db: Session = Depends(get_db), page: int = 1, page_size: int = 100):
    db = next(db)
    query = db.query(Competitor).order_by(desc(Competitor.avg_rating))
    total = query.count()
    data = query.offset((page-1)*page_size).limit(page_size).all()
    rows = [{"business_name": c.business_name, "sector": c.sector, "county": c.county, "address": c.address, "rating": c.avg_rating, "review_count": c.review_count, "lat": c.lat, "lng": c.lng} for c in data]
    return {"count": total, "data": rows}

@router.get("/api/price-oracle")
def get_price_oracle(db: Session = Depends(get_db), page: int = 1, page_size: int = 100):
    db = next(db)
    query = db.query(MarketMetric).filter(MarketMetric.metric_type == "price_avg").order_by(desc(MarketMetric.updated_at))
    total = query.count()
    data = query.offset((page-1)*page_size).limit(page_size).all()
    rows = [{"sector": p.sector, "county": p.county, "price_kes": p.metric_value} for p in data]
    return {"count": total, "data": rows}

@router.get("/api/demand")
def get_demand(db: Session = Depends(get_db), page: int = 1, page_size: int = 100):
    db = next(db)
    query = db.query(MarketMetric).filter(MarketMetric.metric_type == "demand_score").order_by(desc(MarketMetric.metric_value))
    total = query.count()
    data = query.offset((page-1)*page_size).limit(page_size).all()
    rows = [{"sector": d.sector, "county": d.county, "sub_county": d.sub_county, "demand_score": d.metric_value} for d in data]
    return {"count": total, "data": rows}

@router.get("/api/county")
def get_county(db: Session = Depends(get_db)):
    db = next(db)
    counties = db.query(MarketSearch.county, func.sum(MarketSearch.market_size_kes), func.avg(MarketSearch.growth_rate), func.count(MarketSearch.id)).group_by(MarketSearch.county).all()
    data = [{"county": c[0], "market_size": float(c[1] or 0), "growth": float(c[2] or 0), "volume": c[3]} for c in counties]
    return {"count": len(data), "data": data}

@router.get("/api/consumer")
def get_consumer(db: Session = Depends(get_db)):
    db = next(db)
    searches = db.query(MarketSearch.sector, func.count(MarketSearch.id)).group_by(MarketSearch.sector).order_by(desc(func.count(MarketSearch.id))).all()
    data = [{"sector": s[0], "count": s[1]} for s in searches]
    return {"count": len(data), "data": data}

@router.get("/api/risk")
def get_risk(db: Session = Depends(get_db)):
    db = next(db)
    risk_zones = db.query(MarketSearch).filter(MarketSearch.demand_level == "High").all()
    data = [{"county": r.county, "sector": r.sector, "market_size": r.market_size_kes} for r in risk_zones]
    return {"count": len(data), "data": data}

@router.get("/api/policy")
def get_policy(db: Session = Depends(get_db)): db = next(db); return {"count": 0, "data": []}
@router.get("/api/funding")
def get_funding(db: Session = Depends(get_db)): db = next(db); return {"count": 0, "data": []}
@router.get("/api/export")
def get_export(db: Session = Depends(get_db)): db = next(db); return {"count": 0, "data": []}

@router.post("/api/chat")
def chat(message: dict, db: Session = Depends(get_db)):
    db = next(db)
    return {"reply": generate_insights(message.get("message", ""), db)}

# ========== DASHBOARD WITH LIVE TABLES ==========
@router.get("/", include_in_schema=False)
def root(): return RedirectResponse(url="/dashboard")

@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return """<!DOCTYPE html><html><head><title>EvidLens</title><style>
    body{margin:0;font-family:Inter,Arial;background:#ffffff}
  .header{background:#0f172a;padding:20px 40px;display:flex;align-items:center;gap:12px}
  .header h1{color:white;margin:0;font-size:22px}.header p{color:#38bdf8;margin:0;font-size:12px}
  .container{padding:30px 40px;max-width:1400px;margin:0 auto}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:30px}
  .stat-card{background:white;border:2px solid #38bdf8;border-radius:12px;padding:20px}
  .stat-label{color:#64748b;font-size:14px}.stat-value{font-size:32px;font-weight:bold;color:#0f172a;margin-top:5px}
  .banner{background:linear-gradient(90deg,#0ea5e9,#06b6d4);padding:30px;border-radius:16px;color:white;margin-bottom:30px}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
  .card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:24px;color:#0f172a;cursor:pointer;transition:0.2s}
  .card:hover{box-shadow:0 8px 24px rgba(14,165,233,0.2);transform:translateY(-2px)}
  .icon{width:48px;height:48px;background:linear-gradient(135deg,#38bdf8,#0ea5e9);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px;margin-bottom:16px}
  .title{font-weight:600;font-size:16px;margin-bottom:4px}.subtitle{color:#64748b;font-size:12px;margin-bottom:4px}
  .live{color:#f97316;font-size:12px;font-weight:600}.scroll{max-height:200px;overflow:auto;margin-top:10px}
    table{width:100%;font-size:11px;border-collapse:collapse} th,td{padding:6px;border-bottom:1px solid #f1f5f9;text-align:left}
  .footer{background:#1e3a8a;color:white;padding:40px;margin-top:50px}.chat-btn{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#0ea5e9;color:white;border:none;font-size:24px;cursor:pointer}

    /* MODAL */
  .modal{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.6)}
  .modal-content{background:white;margin:5% auto;padding:30px;border-radius:16px;width:90%;max-width:1200px;max-height:80vh;overflow:auto}
  .close{float:right;font-size:28px;font-weight:bold;cursor:pointer;color:#64748b}
  .close:hover{color:#0f172a}
  .search-box{width:100%;padding:12px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:20px;font-size:14px}
    </style></head><body>
    <div class="header"><div style="background:white;padding:8px;border-radius:8px;font-weight:bold;color:#0f172a">EL</div><div><h1>EvidLens</h1><p>Decision Intelligence</p></div></div>
    <div class="container">
        <div class="stats"><div class="stat-card"><div class="stat-label">Total Insights</div><div class="stat-value" id="total">0</div></div><div class="stat-card"><div class="stat-label">Active Lanes</div><div class="stat-value">9</div></div><div class="stat-card"><div class="stat-label">Reports Generated</div><div class="stat-value">0</div></div><div class="stat-card"><div class="stat-label">AI Queries</div><div class="stat-value">0</div></div></div>
        <div class="banner"><div>MARKET INTEL</div><div style="font-size:24px;font-weight:bold">Services Online</div></div>
        <h2>WAVE 2 Intelligence Modules</h2><div class="grid" id="grid">Loading...</div>
    </div>
    <div class="footer"><p style="text-align:center">© 2026 EvidLens. Decision Intelligence for Kenya.</p></div>
    <button class="chat-btn" onclick="alert('Chat: Ask me about any market')">💬</button>

    <div id="detailModal" class="modal"><div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <h2 id="modalTitle"></h2>
        <input type="text" id="searchBox" class="search-box" placeholder="Search..." onkeyup="filterTable()">
        <div id="modalTable"></div>
    </div></div>

    <script>
    let currentData = [];
    async function loadStats(){let s=await fetch('/api/stats').then(r=>r.json());document.getElementById('total').innerText=s.total_insights}

    const modules=[{key:"competitive",title:"Competitive Engine",icon:"🎯"},{key:"price-oracle",title:"Price Oracle",icon:"💰"},{key:"demand",title:"Demand Radar",icon:"📈"},{key:"county",title:"County Mapper",icon:"🗺️"},{key:"consumer",title:"Consumer Pulse",icon:"👥"},{key:"risk",title:"Risk Sentinel",icon:"⚠️"},{key:"policy",title:"Policy Watch",icon:"📜"},{key:"funding",title:"Funding Radar",icon:"🏦"},{key:"export",title:"Export Navigator",icon:"🚢"}];

    async function loadCards(){let html='';for(let m of modules){let res=await fetch(`/api/${m.key}?page=1&page_size=50`).then(r=>r.json());html+=`<div class="card" onclick="openModal('${m.key}','${m.title}')"><div class="icon">${m.icon}</div><div class="title">${m.title}</div><div class="subtitle">${res.count} Records</div><div class="scroll"><table>`;if(res.count>0){res.data.slice(0,5).forEach(r=>{html+=`<tr><td>${Object.values(r).slice(0,3).join('</td><td>')}</td></tr>`})}else{html+=`<tr><td>0 records. Ready for data.</td></tr>`}html+=`</table></div><div class="live">CLICK TO VIEW ALL →</div></div>`}document.getElementById('grid').innerHTML=html}

    async function openModal(key,title){document.getElementById('modalTitle').innerText=title;document.getElementById('detailModal').style.display='block';let res=await fetch(`/api/${key}?page=1&page_size=500`).then(r=>r.json());currentData=res.data;renderTable(currentData)}
    function closeModal(){document.getElementById('detailModal').style.display='none'}
    function renderTable(data){if(data.length==0){document.getElementById('modalTable').innerHTML='<p>No data yet</p>';return}let headers=Object.keys(data[0]);let html='<table><tr>'+headers.map(h=>`<th>${h}</th>`).join('')+'</tr>';data.forEach(r=>{html+='<tr>'+headers.map(h=>`<td>${r[h]||''}</td>`).join('')+'</tr>'});html+='</table>';document.getElementById('modalTable').innerHTML=html}
    function filterTable(){let val=document.getElementById('searchBox').value.toLowerCase();let filtered=currentData.filter(r=>JSON.stringify(r).toLowerCase().includes(val));renderTable(filtered)}
    window.onclick=function(e){if(e.target==document.getElementById('detailModal'))closeModal()}
    loadStats();loadCards();
    </script></body></html>"""
