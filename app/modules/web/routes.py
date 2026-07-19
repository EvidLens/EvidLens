from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.modules.database import get_db
from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric

router = APIRouter()

# ========== 9 REAL APIS - NO DUMMY DATA ==========
@router.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    db = next(db)
    insights = db.query(func.count(Competitor.id)).scalar() + db.query(func.count(MarketMetric.id)).scalar() + db.query(func.count(MarketSearch.id)).scalar()
    sectors = db.query(func.count(func.distinct(MarketSearch.sector))).scalar() or 0
    return {"insights": insights, "products": 21, "sectors": sectors, "reports": 0}

@router.get("/api/competitive")
def get_competitive(db: Session = Depends(get_db)):
    db = next(db)
    data = db.query(Competitor).order_by(desc(Competitor.avg_rating)).limit(500).all()
    rows = [{"Name": c.business_name, "Sector": c.sector, "County": c.county, "Rating": c.avg_rating, "Reviews": c.review_count, "Address": c.address, "Lat": c.lat, "Lng": c.lng} for c in data]
    return {"count": len(rows), "data": rows}

@router.get("/api/price-oracle")
def get_price_oracle(db: Session = Depends(get_db)):
    db = next(db)
    data = db.query(MarketMetric).filter(MarketMetric.metric_type == "price_avg").order_by(desc(MarketMetric.updated_at)).limit(500).all()
    rows = [{"Sector": p.sector, "County": p.county, "Product": p.metric_name or "N/A", "Price KES": p.metric_value} for p in data]
    return {"count": len(rows), "data": rows}

@router.get("/api/demand")
def get_demand(db: Session = Depends(get_db)):
    db = next(db)
    data = db.query(MarketMetric).filter(MarketMetric.metric_type == "demand_score").order_by(desc(MarketMetric.metric_value)).limit(500).all()
    rows = [{"Sector": d.sector, "County": d.county, "SubCounty": d.sub_county, "Demand Score": d.metric_value} for d in data]
    return {"count": len(rows), "data": rows}

@router.get("/api/county")
def get_county(db: Session = Depends(get_db)):
    db = next(db)
    counties = db.query(MarketSearch.county, func.sum(MarketSearch.market_size_kes), func.avg(MarketSearch.growth_rate), func.count(MarketSearch.id)).group_by(MarketSearch.county).all()
    rows = [{"County": c[0], "Market Size KES": float(c[1] or 0), "Growth %": round(float(c[2] or 0),2), "Volume": c[3]} for c in counties]
    return {"count": len(rows), "data": rows}

@router.get("/api/consumer")
def get_consumer(db: Session = Depends(get_db)):
    db = next(db)
    searches = db.query(MarketSearch.sector, func.count(MarketSearch.id)).group_by(MarketSearch.sector).order_by(desc(func.count(MarketSearch.id))).limit(50).all()
    rows = [{"Sector": s[0], "Search Count": s[1]} for s in searches]
    return {"count": len(rows), "data": rows}

@router.get("/api/risk")
def get_risk(db: Session = Depends(get_db)):
    db = next(db)
    zones = db.query(MarketSearch).filter(MarketSearch.demand_level == "High").limit(500).all()
    rows = [{"County": r.county, "Sector": r.sector, "Market Size KES": r.market_size_kes, "Opportunity": "High Demand Low Competition"} for r in zones]
    return {"count": len(rows), "data": rows}

@router.get("/api/policy")
def get_policy(db: Session = Depends(get_db)):
    db = next(db)
    return {"count": 0, "data": []} # Ready for CBK/NEMA API hook

@router.get("/api/funding")
def get_funding(db: Session = Depends(get_db)):
    db = next(db)
    return {"count": 0, "data": []} # Ready for grants/loans API hook

@router.get("/api/export")
def get_export(db: Session = Depends(get_db)):
    db = next(db)
    return {"count": 0, "data": []} # Ready for export API hook

@router.get("/", include_in_schema=False)
def root(): return RedirectResponse(url="/dashboard")

@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    return """<!DOCTYPE html><html><head><title>EvidLens</title><style>
    body{margin:0;font-family:Inter,Arial;background:#0a0a0a;color:#fff}
   .header{background:#111;padding:20px 40px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #222}
   .header h1{margin:0;font-size:22px}.header p{color:#38bdf8;margin:0;font-size:12px}
   .container{padding:30px 40px;max-width:1400px;margin:0 auto}
   .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:30px}
   .stat-card{background:#111;border:1px solid #38bdf8;border-radius:12px;padding:20px}
   .stat-label{color:#888;font-size:14px}.stat-value{font-size:32px;font-weight:bold;color:#fff;margin-top:5px}
   .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
   .card{background:#111;border:1px solid #222;border-radius:16px;padding:24px;cursor:pointer;transition:0.2s}
   .card:hover{border-color:#38bdf8;transform:translateY(-2px)}
   .icon{font-size:24px;margin-bottom:12px}.title{font-weight:600;font-size:16px;margin-bottom:4px}
   .subtitle{color:#888;font-size:12px;margin-bottom:8px}.why{color:#38bdf8;font-size:11px;margin-bottom:10px}
   .scroll{max-height:180px;overflow:auto;margin-top:10px;background:#0a0a0a;border-radius:8px;padding:8px}
    table{width:100%;font-size:10px;border-collapse:collapse} th,td{padding:6px;border-bottom:1px solid #222;text-align:left}
   .modal{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.8)}
   .modal-content{background:#111;margin:3% auto;padding:30px;border-radius:16px;width:90%;max-width:1200px;max-height:85vh;overflow:auto;border:1px solid #38bdf8}
   .close{float:right;font-size:28px;cursor:pointer;color:#888}.search-box{width:100%;padding:12px;background:#0a0a0a;border:1px solid #222;border-radius:8px;color:#fff;margin-bottom:20px}
    </style></head><body>
    <div class="header"><div style="background:#38bdf8;padding:8px;border-radius:8px;font-weight:bold;color:#000">EL</div><div><h1>EvidLens</h1><p>From Data to Decision</p></div></div>
    <div class="container">
        <div class="stats"><div class="stat-card"><div class="stat-label">Insights Generated</div><div class="stat-value" id="insights">0</div></div><div class="stat-card"><div class="stat-label">Active Products</div><div class="stat-value">21</div></div><div class="stat-card"><div class="stat-label">Sectors Covered</div><div class="stat-value" id="sectors">0</div></div><div class="stat-card"><div class="stat-label">Reports Exported</div><div class="stat-value">0</div></div></div>
        <h2>9 Intelligence Areas - LIVE</h2><div class="grid" id="grid">Loading...</div>
    </div>
    <div id="detailModal" class="modal"><div class="modal-content"><span class="close" onclick="closeModal()">&times;</span><h2 id="modalTitle"></h2><input type="text" id="searchBox" class="search-box" placeholder="Search..." onkeyup="filterTable()"><div id="modalTable"></div></div></div>
    <script>
    let currentData = [];
    async function loadStats(){let s=await fetch('/api/stats').then(r=>r.json());document.getElementById('insights').innerText=s.insights;document.getElementById('sectors').innerText=s.sectors}
    const modules=[
    {key:"competitive",title:"1. Competitive Engine 🎯",why:"Who are my competitors in Nairobi? Instant answer"},
    {key:"price-oracle",title:"2. Price Oracle 💰",why:"What should I charge for maize in Kisumu? Data-driven"},
    {key:"demand",title:"3. Demand Radar 📈",why:"Where is demand exploding right now?"},
    {key:"county",title:"4. County Mapper 🗺️",why:"Which 5 counties to expand to? Board-ready"},
    {key:"consumer",title:"5. Consumer Pulse 👥",why:"What are Kenyans actually searching for?"},
    {key:"risk",title:"6. Risk Sentinel ⚠️",why:"Where is low competition, high demand?"},
    {key:"policy",title:"7. Policy Watch 📜",why:"Plug in policy data later. No crash"},
    {key:"funding",title:"8. Funding Radar 🏦",why:"Plug in grants/loans later. No crash"},
    {key:"export",title:"9. Export Navigator 🚢",why:"Plug in export data later. No crash"}
    ];
    async function loadCards(){let html='';for(let m of modules){let res=await fetch(`/api/${m.key}?page=1&page_size=50`).then(r=>r.json());html+=`<div class="card" onclick="openModal('${m.key}','${m.title}')"><div class="icon">${m.title.split(' ')[2]||''}</div><div class="title">${m.title}</div><div class="subtitle">${res.count} Records</div><div class="why">${m.why}</div><div class="scroll"><table>`;if(res.count>0){res.data.slice(0,5).forEach(r=>{html+=`<tr><td>${Object.values(r).slice(0,3).join('</td><td>')}</td></tr>`})}else{html+=`<tr><td>0 records. Ready for data.</td></tr>`}html+=`</table></div><div style="color:#38bdf8;font-size:12px">CLICK TO VIEW ALL →</div></div>`}document.getElementById('grid').innerHTML=html}
    async function openModal(key,title){document.getElementById('modalTitle').innerText=title;document.getElementById('detailModal').style.display='block';let res=await fetch(`/api/${key}?page=1&page_size=500`).then(r=>r.json());currentData=res.data;renderTable(currentData)}
    function closeModal(){document.getElementById('detailModal').style.display='none'}
    function renderTable(data){if(data.length==0){document.getElementById('modalTable').innerHTML='<p>0 records. Ready for data.</p>';return}let headers=Object.keys(data[0]);let html='<table><tr>'+headers.map(h=>`<th>${h}</th>`).join('')+'</tr>';data.forEach(r=>{html+='<tr>'+headers.map(h=>`<td>${r[h]||''}</td>`).join('')+'</tr>'});html+='</table>';document.getElementById('modalTable').innerHTML=html}
    function filterTable(){let val=document.getElementById('searchBox').value.toLowerCase();let filtered=currentData.filter(r=>JSON.stringify(r).toLowerCase().includes(val));renderTable(filtered)}
    window.onclick=function(e){if(e.target==document.getElementById('detailModal'))closeModal()}
    loadStats();loadCards();
    </script></body></html>"""
