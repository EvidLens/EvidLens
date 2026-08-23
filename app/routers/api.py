from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, desc, or_
import io, csv, os, requests
from datetime import datetime, timedelta

from app.modules.lens_engine.service import LensEngineService
from app.core.db import get_session as get_db
from app.core.models import MarketMetric, Company, NewsArticle, SocialMention, ExportOpportunity
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user

router = APIRouter()

PRICING = {
    "BASIC": {"monthly": 999, "yearly": 9990},
    "PROFESSIONAL": {"monthly": 2999, "yearly": 29990},
    "ENTERPRISE": {"monthly": 9999, "yearly": 99990}
}
ADDONS = {"extra_credits": 500, "priority_support": 1000}
ALC = {"BASIC": 10, "PROFESSIONAL": 100, "ENTERPRISE": 99999}

MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")
DARAJA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
DARAJA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "https://evidlens.co.ke/api/mpesa-callback")
DARAJA_CONSUMER_KEY = os.getenv("DARAJA_CONSUMER_KEY", "")
DARAJA_CONSUMER_SECRET = os.getenv("DARAJA_CONSUMER_SECRET", "")

def get_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def get_password(shortcode, passkey, timestamp):
    import base64
    return base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

def get_daraja_token():
    if not DARAJA_CONSUMER_KEY: return "mock-token"
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(DARAJA_CONSUMER_KEY, DARAJA_CONSUMER_SECRET))
    return r.json().get("access_token", "mock-token")

def apply_sort(query, model, sort_by, order):
    column = getattr(model, sort_by, model.id)
    if order == "desc":
        return query.order_by(desc(column))
    return query.order_by(column)

@router.get("/api/market/risk")
def risk_sentinel_api(db: Session = Depends(get_db)):
    news = db.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(10)).all()
    return {"risk_alerts": [n.model_dump() for n in news]}

@router.get("/api/market/export")
def export_navigator_api(db: Session = Depends(get_db)):
    exports = db.exec(select(ExportOpportunity).limit(20)).all()
    return {"export_opportunities": [e.model_dump() for e in exports]}

@router.get("/api/sectors")
def get_sectors(search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.sector))
    if search: q = q.where(MarketMetric.sector.contains(search))
    return {"sectors": [s[0] for s in db.exec(q).all() if s[0]]}

@router.get("/api/counties")
def get_counties(search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.county))
    if search: q = q.where(MarketMetric.county.contains(search))
    return {"counties": [c[0] for c in db.exec(q).all() if c[0]]}

@router.get("/api/subcounties")
def get_subcounties(county: str = "", search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.subcounty)).where(MarketMetric.county == county) if county else select(func.distinct(MarketMetric.subcounty))
    if search: q = q.where(MarketMetric.subcounty.contains(search))
    return {"subcounties": [s[0] for s in db.exec(q).all() if s[0]]}

@router.get("/api/products")
def get_products(search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.product))
    if search: q = q.where(MarketMetric.product.contains(search))
    return {"products": [p[0] for p in db.exec(q).all() if p[0]]}

@router.get("/api/companies")
def get_companies(search: str = "", sector: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "id", order: str = "desc", db: Session = Depends(get_db)):
    q = select(Company)
    if search: q = q.where(or_(Company.name.ilike(f"%{search}%"), Company.sector.ilike(f"%{search}%"), Company.county.ilike(f"%{search}%")))
    if sector: q = q.where(Company.sector == sector)
    if county: q = q.where(Company.county == county)
    total = len(db.exec(q).all())
    q = apply_sort(q, Company, sort_by, order)
    data = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": [c.model_dump() for c in data], "total": total, "page": page}

@router.get("/api/prices")
def get_prices(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "avg_price_kes", order: str = "desc", db: Session = Depends(get_db)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(db.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"prices": [p.model_dump() for p in data], "total": total, "page": page}

@router.get("/api/demand")
def get_demand(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", db: Session = Depends(get_db)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(db.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"demand": [m.model_dump() for m in data], "total": total, "page": page}

@router.get("/api/county-stats")
def get_county_stats(search: str = "", page: int = 1, limit: int = 47, sort_by: str = "market_size", order: str = "desc", db: Session = Depends(get_db)):
    q = select(MarketMetric.county, func.sum(MarketMetric.avg_price_kes).label("market_size"), func.avg(MarketMetric.demand_score).label("growth"), func.count(MarketMetric.id).label("volume")).group_by(MarketMetric.county)
    if search: q = q.where(MarketMetric.county.contains(search))
    data = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    stats = [dict(r._mapping) for r in data]
    stats.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=(order=="desc"))
    return {"stats": stats, "total": 47, "page": page}

@router.get("/api/top-sectors")
def get_top_sectors(search: str = "", page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    q = select(MarketMetric.sector, func.count(MarketMetric.id).label("count")).group_by(MarketMetric.sector)
    if search: q = q.where(MarketMetric.sector.contains(search))
    total = len(db.exec(q).all())
    data = db.exec(q.order_by(func.count(MarketMetric.id).desc()).offset((page-1)*limit).limit(limit)).all()
    return {"sectors": [dict(r._mapping) for r in data], "total": total, "page": page}

@router.get("/api/opportunities")
def get_opportunities(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", db: Session = Depends(get_db)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(db.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = db.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"opportunities": [m.model_dump() for m in data], "total": total, "page": page}

@router.get("/api/lens/insights")
async def get_lens_insights(sector: str = Query(...), county: str = None, db: Session = Depends(get_db)):
    try:
        from app.modules.lens_engine.service import LensEngineService
        service = LensEngineService(db)
        return await service.generate_sector_insights(sector, county)
    except Exception as e:
        return {"sector": sector, "county": county, "insights": [], "error": str(e)}

@router.get("/api/export/{table}")
def export_csv(table: str, search: str = "", db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    if table == "companies":
        data = db.exec(select(Company)).all()
        writer.writerow(["Name","Sector","County","Rating","Reviews","Address","Lat","Lng"])
        [writer.writerow([r.name, r.sector, r.county, 0, 0, r.county, 0, 0]) for r in data]
    elif table == "prices":
        data = db.exec(select(MarketMetric)).all()
        writer.writerow(["Product","Price","County","Market","Source","FetchedAt"])
        [writer.writerow([r.product, r.avg_price_kes, r.county, r.company_name or "", "KPIN", r.created_at]) for r in data]
    elif table == "demand":
        data = db.exec(select(MarketMetric)).all()
        writer.writerow(["Product","Sector","County","DemandScore","MarketSizeKES","Growth%","Volume","OpportunityScore"])
        [writer.writerow([r.product, r.sector, r.county, r.demand_score, r.avg_price_kes, 0, 0, 0]) for r in data]
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"})

@router.get("/api/social-feed")
def get_social_feed(platform: str = "all", db: Session = Depends(get_db)):
    q = select(SocialMention).order_by(SocialMention.created_at.desc()).limit(20)
    if platform!= "all": q = q.where(SocialMention.platform == platform)
    return {"posts": [p.model_dump() for p in db.exec(q).all()]}

@router.get("/api/news-feed")
def get_news_feed(db: Session = Depends(get_db)):
    return {"articles": [n.model_dump() for n in db.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(20)).all()]}

@router.get("/api/pricing")
def api_pricing(): return {"plans": PRICING, "addons": ADDONS, "alc": ALC}

@router.post("/api/checkout")
def mpesa_stk_push(payload: dict, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = payload.get("plan", "BASIC")
    billing_cycle = payload.get("billing", "monthly")
    phone = payload.get("phone", "")
    price = PRICING.get(plan, PRICING["BASIC"]).get(billing_cycle, 999)
    token = get_daraja_token()
    timestamp = get_timestamp()
    password = get_password(DARAJA_SHORTCODE, DARAJA_PASSKEY, timestamp)
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {token}"}
    mpesa_payload = {"BusinessShortCode": DARAJA_SHORTCODE,"Password": password,"Timestamp": timestamp,"TransactionType": "CustomerPayBillOnline","Amount": price,"PartyA": phone,"PartyB": DARAJA_SHORTCODE,"PhoneNumber": phone,"CallBackURL": MPESA_CALLBACK_URL,"AccountReference": f"EvidLens-{plan}-{user.id}","TransactionDesc": f"{plan} {billing_cycle} Subscription"}
    try:
        r = requests.post(api_url, json=mpesa_payload, headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e), "mock": mpesa_payload}

@router.post("/api/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        stk = data["Body"]["stkCallback"]
        if stk["ResultCode"] == 0:
            print(f"MPESA SUCCESS: {stk}")
    except Exception as e:
        print(f"MPESA CALLBACK ERROR: {e}")
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.post("/api/run-scraper")
def run_scraper():
    try:
        from app.modules.lens_engine.service import scrape_kpin_prices, fetch_real_news, fetch_real_tweets
        scrape_kpin_prices()
        fetch_real_news()
        fetch_real_tweets()
        return {"status": "scraper ran. DB updated with real prices"}
    except Exception as e:
        return {"status": "scraper failed", "error": str(e)}

@router.post("/api/lens/chat")
async def lens_chat(payload: dict, db: Session = Depends(get_db)):
    msg = payload.get("message", "hi")
    sector = payload.get("sector")
    county = payload.get("county")
    service = LensEngineService(db)
    result = await service.chat(msg, payload.get("email","anon@evidlens.co.ke"))
    # result is {"reply": "..."} already, but handle both cases
    if isinstance(result, dict):
        return result
    return {"reply": result}
