from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, desc, or_
import io, csv, os, re, requests, base64
from datetime import datetime

from app.modules.lens_engine.service import LensEngineService
from app.core.db import get_session as get_db
from app.core.models import MarketMetric, Company, NewsArticle, SocialMention, ExportOpportunity
from app.modules.auth.models import AuthUser
from app.modules.auth.dependencies import get_current_user, get_current_user_optional

router = APIRouter()

PRICING = {
    "BASIC": {"monthly": 500, "yearly": 5000},
    "PROFESSIONAL": {"monthly": 1500, "yearly": 15000},
    "ENTERPRISE": {"monthly": 5000, "yearly": 50000}
}
ADDONS = {"extra_credits_5": 500, "priority_support_basic_only": 250}
ALC = {"BASIC": 10, "PROFESSIONAL": 100, "ENTERPRISE": 10000}
CREDIT_PACKAGES = {"5": 500, "20": 1800, "50": 4000}

MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")
DARAJA_SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")
DARAJA_PASSKEY = os.getenv("MPESA_PASSKEY", "")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "https://evidlens.co.ke/api/mpesa-callback")
DARAJA_CONSUMER_KEY = os.getenv("DARAJA_CONSUMER_KEY", "")
DARAJA_CONSUMER_SECRET = os.getenv("DARAJA_CONSUMER_SECRET", "")

SORT_WHITELIST = {
    "Company": {"id", "name", "sector", "county"},
    "MarketMetric": {"id", "avg_price_kes", "demand_score", "product", "county", "created_at", "timestamp"},
}

def get_timestamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")

def get_password(shortcode, passkey, timestamp):
    return base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()

def normalize_phone(raw: str) -> str:
    p = re.sub(r"\D", "", str(raw or ""))
    if p.startswith("0"):
        p = "254" + p[1:]
    if not re.fullmatch(r"254(7|1)\d{8}", p):
        raise HTTPException(status_code=400, detail="Enter a valid Kenyan phone: 07XXXXXXXX, 01XXXXXXXX, or 2547XXXXXXXX")
    return p

def get_daraja_token():
    if not DARAJA_CONSUMER_KEY or not DARAJA_CONSUMER_SECRET:
        raise HTTPException(status_code=503, detail="M-Pesa is not configured. Try again later.")
    base = "https://sandbox.safaricom.co.ke" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"
    try:
        r = requests.get(f"{base}/oauth/v1/generate?grant_type=client_credentials", auth=(DARAJA_CONSUMER_KEY, DARAJA_CONSUMER_SECRET), timeout=10)
        r.raise_for_status()
        token = r.json().get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="Could not get M-Pesa token.")
        return token
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach M-Pesa. Try again.")

def apply_sort(query, model, sort_by, order):
    allowed = SORT_WHITELIST.get(model.__name__, {"id"})
    if sort_by not in allowed:
        sort_by = "id"
    column = getattr(model, sort_by, model.id)
    if order == "desc":
        return query.order_by(desc(column))
    return query.order_by(column)

def count_query(db: Session, q):
    return db.exec(select(func.count()).select_from(q.subquery())).first() or 0

def paginate_params(page: int, limit: int):
    page = max(1, page)
    limit = min(max(1, limit), 100)
    return page, limit

@router.get("/api/market/risk")
def risk_sentinel_api(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    news = db.exec(select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(10)).all()
    return {"risk_alerts": [n.model_dump() if hasattr(n, "model_dump") else {"title": getattr(n, "title", "-")} for n in news]}

@router.get("/api/market/export")
def export_navigator_api(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    exports = db.exec(select(ExportOpportunity).limit(20)).all()
    return {"export_opportunities": [e.model_dump() if hasattr(e, "model_dump") else {} for e in exports]}

@router.get("/api/sectors")
def get_sectors(search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.sector))
    if search:
        q = q.where(MarketMetric.sector.ilike(f"%{search}%"))
    return {"sectors": [s[0] for s in db.exec(q).all() if s and s[0]]}

@router.get("/api/counties")
def get_counties(search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.county))
    if search:
        q = q.where(MarketMetric.county.ilike(f"%{search}%"))
    return {"counties": [c[0] for c in db.exec(q).all() if c and c[0]]}

@router.get("/api/subcounties")
def get_subcounties(county: str = "", search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.subcounty))
    if county:
        q = q.where(MarketMetric.county == county)
    if search:
        q = q.where(MarketMetric.subcounty.ilike(f"%{search}%"))
    return {"subcounties": [s[0] for s in db.exec(q).all() if s and s[0]]}

@router.get("/api/products")
def get_products(search: str = "", db: Session = Depends(get_db)):
    q = select(func.distinct(MarketMetric.product))
    if search:
        q = q.where(MarketMetric.product.ilike(f"%{search}%"))
    return {"products": [p[0] for p in db.exec(q).all() if p and p[0]]}

@router.get("/api/companies")
def get_companies(search: str = "", sector: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "id", order: str = "desc", db: Session = Depends(get_db)):
    page, limit = paginate_params(page, limit)
    q = select(Company)
    if search:
        q = q.where(or_(Company.name.ilike(f"%{search}%"), Company.sector.ilike(f"%{search}%"), Company.county.ilike(f"%{search}%")))
    if sector:
        q = q.where(Company.sector == sector)
    if county:
        q = q.where(Company.county == county)
    total = count_query(db, q)
    q = apply_sort(q, Company, sort_by, order)
    data = db.exec(q.offset((page - 1) * limit).limit(limit)).all()
    return {"companies": [c.model_dump() for c in data], "total": total, "page": page, "limit": limit}

@router.get("/api/prices")
def get_prices(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "avg_price_kes", order: str = "desc", db: Session = Depends(get_db)):
    page, limit = paginate_params(page, limit)
    q = select(MarketMetric)
    if search:
        q = q.where(or_(MarketMetric.product.ilike(f"%{search}%"), MarketMetric.county.ilike(f"%{search}%")))
    if product:
        q = q.where(MarketMetric.product == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = count_query(db, q)
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = db.exec(q.offset((page - 1) * limit).limit(limit)).all()
    return {"prices": [p.model_dump() for p in data], "total": total, "page": page, "limit": limit}

@router.get("/api/demand")
def get_demand(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", db: Session = Depends(get_db)):
    page, limit = paginate_params(page, limit)
    q = select(MarketMetric)
    if search:
        q = q.where(or_(MarketMetric.product.ilike(f"%{search}%"), MarketMetric.county.ilike(f"%{search}%")))
    if product:
        q = q.where(MarketMetric.product == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = count_query(db, q)
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = db.exec(q.offset((page - 1) * limit).limit(limit)).all()
    return {"demand": [m.model_dump() for m in data], "total": total, "page": page, "limit": limit}

@router.get("/api/county-stats")
def get_county_stats(search: str = "", page: int = 1, limit: int = 47, sort_by: str = "market_size", order: str = "desc", db: Session = Depends(get_db)):
    page, limit = paginate_params(page, limit)
    q = select(MarketMetric.county, func.sum(MarketMetric.avg_price_kes).label("market_size"), func.avg(MarketMetric.demand_score).label("growth"), func.count(MarketMetric.id).label("volume"))
    if search:
        q = q.where(MarketMetric.county.ilike(f"%{search}%"))
    q = q.group_by(MarketMetric.county)
    data = db.exec(q.offset((page - 1) * limit).limit(limit)).all()
    stats = [dict(r._mapping) for r in data]
    if sort_by in ("market_size", "growth", "volume"):
        stats.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=(order == "desc"))
    total = db.exec(select(func.count(func.distinct(MarketMetric.county)))).first() or 0
    return {"stats": stats, "total": total, "page": page, "limit": limit}

@router.get("/api/top-sectors")
def get_top_sectors(search: str = "", page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    page, limit = paginate_params(page, limit)
    q = select(MarketMetric.sector, func.count(MarketMetric.id).label("count"))
    if search:
        q = q.where(MarketMetric.sector.ilike(f"%{search}%"))
    q = q.group_by(MarketMetric.sector)
    total = len(db.exec(q).all())
    data = db.exec(q.order_by(desc(func.count(MarketMetric.id))).offset((page - 1) * limit).limit(limit)).all()
    return {"sectors": [dict(r._mapping) for r in data], "total": total, "page": page, "limit": limit}

@router.get("/api/opportunities")
def get_opportunities(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", db: Session = Depends(get_db)):
    page, limit = paginate_params(page, limit)
    q = select(MarketMetric)
    if search:
        q = q.where(or_(MarketMetric.product.ilike(f"%{search}%"), MarketMetric.county.ilike(f"%{search}%")))
    if product:
        q = q.where(MarketMetric.product == product)
    if county:
        q = q.where(MarketMetric.county == county)
    total = count_query(db, q)
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = db.exec(q.offset((page - 1) * limit).limit(limit)).all()
    return {"opportunities": [m.model_dump() for m in data], "total": total, "page": page, "limit": limit}

@router.get("/api/lens/insights")
async def get_lens_insights(sector: str = Query(...), county: str = None, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user_optional)):
    try:
        service = LensEngineService(db)
        return await service.generate_sector_insights(sector, county)
    except Exception as e:
        return {"sector": sector, "county": county, "insights": [], "error": str(e)}

@router.get("/api/export/{table}")
def export_csv(table: str, search: str = "", db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    if table not in ("companies", "prices", "demand"):
        raise HTTPException(status_code=400, detail="Invalid export table.")
    output = io.StringIO()
    writer = csv.writer(output)
    if table == "companies":
        q = select(Company)
        if search:
            q = q.where(or_(Company.name.ilike(f"%{search}%"), Company.sector.ilike(f"%{search}%"), Company.county.ilike(f"%{search}%")))
        data = db.exec(q.limit(5000)).all()
        writer.writerow(["Name", "Sector", "County", "Rating", "Reviews", "Address", "Lat", "Lng"])
        for r in data:
            writer.writerow([r.name, r.sector, r.county, getattr(r, "rating", "") or "", getattr(r, "reviews", "") or "", getattr(r, "address", "") or r.county or "", getattr(r, "lat", "") or "", getattr(r, "lng", "") or ""])
    elif table == "prices":
        q = select(MarketMetric)
        if search:
            q = q.where(or_(MarketMetric.product.ilike(f"%{search}%"), MarketMetric.county.ilike(f"%{search}%")))
        data = db.exec(q.limit(5000)).all()
        writer.writerow(["Product", "Price", "County", "Market", "Source", "FetchedAt"])
        for r in data:
            writer.writerow([r.product, r.avg_price_kes, r.county, getattr(r, "company_name", "") or "", "KPIN", r.created_at])
    elif table == "demand":
        q = select(MarketMetric)
        if search:
            q = q.where(or_(MarketMetric.product.ilike(f"%{search}%"), MarketMetric.county.ilike(f"%{search}%")))
        data = db.exec(q.limit(5000)).all()
        writer.writerow(["Product", "Sector", "County", "DemandScore", "MarketSizeKES", "Growth%", "Volume", "OpportunityScore"])
        for r in data:
            writer.writerow([r.product, r.sector, r.county, r.demand_score, r.avg_price_kes, getattr(r, "growth", "") or "", getattr(r, "volume", "") or "", getattr(r, "opportunity_score", "") or ""])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"})

@router.get("/api/social-feed")
def get_social_feed(platform: str = "all", db: Session = Depends(get_db)):
    q = select(SocialMention).order_by(desc(SocialMention.created_at)).limit(20)
    if platform != "all":
        q = q.where(SocialMention.platform == platform)
    return {"posts": [p.model_dump() for p in db.exec(q).all()]}

@router.get("/api/news-feed")
def get_news_feed(db: Session = Depends(get_db)):
    return {"articles": [n.model_dump() for n in db.exec(select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(20)).all()]}

@router.get("/api/pricing")
def api_pricing():
    return {"plans": PRICING, "addons": ADDONS, "alc": ALC, "credit_packages": CREDIT_PACKAGES}

@router.post("/api/checkout")
def mpesa_stk_push(payload: dict, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = str(payload.get("plan", "BASIC")).upper()
    billing_cycle = str(payload.get("billing", "monthly")).lower()
    if plan not in PRICING:
        raise HTTPException(status_code=400, detail="Invalid plan.")
    if billing_cycle not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="Invalid billing cycle.")
    phone = normalize_phone(payload.get("phone") or getattr(user, "phone", "") or "")
    price = PRICING[plan][billing_cycle]
    if not DARAJA_PASSKEY:
        raise HTTPException(status_code=503, detail="M-Pesa is not configured. Try again later.")
    token = get_daraja_token()
    timestamp = get_timestamp()
    password = get_password(DARAJA_SHORTCODE, DARAJA_PASSKEY, timestamp)
    base = "https://sandbox.safaricom.co.ke" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"
    headers = {"Authorization": f"Bearer {token}"}
    mpesa_payload = {"BusinessShortCode": DARAJA_SHORTCODE, "Password": password, "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": price, "PartyA": phone, "PartyB": DARAJA_SHORTCODE, "PhoneNumber": phone, "CallBackURL": MPESA_CALLBACK_URL, "AccountReference": f"EvidLens-{plan}-{user.id}", "TransactionDesc": f"{plan} {billing_cycle} Subscription"}
    try:
        r = requests.post(f"{base}/mpesa/stkpush/v1/processrequest", json=mpesa_payload, headers=headers, timeout=10)
        data = r.json() if r.content else {}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach M-Pesa. Try again.")
    if r.status_code != 200 or data.get("ResponseCode") != "0":
        raise HTTPException(status_code=502, detail=data.get("ResponseDescription") or data.get("errorMessage") or "M-Pesa prompt failed. Try again.")
    return {"message": "M-Pesa prompt sent. Enter your PIN to complete.", "checkout_request_id": data.get("CheckoutRequestID"), "merchant_request_id": data.get("MerchantRequestID")}

@router.post("/api/wallet/buy")
def wallet_buy(payload: dict, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)):
    package = str(payload.get("package") or payload.get("credits") or "")
    if package not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid credit package.")
    phone = normalize_phone(payload.get("phone") or getattr(user, "phone", "") or "")
    amount = CREDIT_PACKAGES[package]
    if not DARAJA_PASSKEY:
        raise HTTPException(status_code=503, detail="M-Pesa is not configured. Try again later.")
    token = get_daraja_token()
    timestamp = get_timestamp()
    password = get_password(DARAJA_SHORTCODE, DARAJA_PASSKEY, timestamp)
    base = "https://sandbox.safaricom.co.ke" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke"
    headers = {"Authorization": f"Bearer {token}"}
    mpesa_payload = {"BusinessShortCode": DARAJA_SHORTCODE, "Password": password, "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": amount, "PartyA": phone, "PartyB": DARAJA_SHORTCODE, "PhoneNumber": phone, "CallBackURL": MPESA_CALLBACK_URL, "AccountReference": f"EvidLens-CREDITS-{package}-{user.id}", "TransactionDesc": f"{package} Credits"}
    try:
        r = requests.post(f"{base}/mpesa/stkpush/v1/processrequest", json=mpesa_payload, headers=headers, timeout=10)
        data = r.json() if r.content else {}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach M-Pesa. Try again.")
    if r.status_code != 200 or data.get("ResponseCode") != "0":
        raise HTTPException(status_code=502, detail=data.get("ResponseDescription") or data.get("errorMessage") or "M-Pesa prompt failed. Try again.")
    return {"message": "M-Pesa prompt sent. Enter your PIN to complete.", "checkout_request_id": data.get("CheckoutRequestID"), "merchant_request_id": data.get("MerchantRequestID")}

@router.post("/api/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except Exception:
        return {"ResultCode": 1, "ResultDesc": "Invalid JSON"}
    try:
        stk = data.get("Body", {}).get("stkCallback", {})
        if stk.get("ResultCode") == 0:
            print(f"MPESA SUCCESS: {stk}")
    except Exception as e:
        print(f"MPESA CALLBACK ERROR: {e}")
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.post("/api/run-scraper")
def run_scraper(user: AuthUser = Depends(get_current_user)):
    if not getattr(user, "is_admin", False) and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Admin only.")
    try:
        from app.modules.lens_engine.service import scrape_kpin_prices, fetch_real_news, fetch_real_tweets
        scrape_kpin_prices()
        fetch_real_news()
        fetch_real_tweets()
        return {"status": "scraper ran. DB updated with real prices"}
    except Exception as e:
        return {"status": "scraper failed", "error": str(e)}

@router.post("/api/lens/chat")
async def lens_chat(payload: dict, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    msg = str(payload.get("message") or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Message is required.")
    if len(msg) > 2000:
        raise HTTPException(status_code=400, detail="Message too long.")
    service = LensEngineService(db)
    result = await service.chat(msg, payload.get("email") or getattr(user, "email", "anon@evidlens.co.ke"))
    if isinstance(result, dict):
        return result
    return {"reply": result}

@router.post("/api/analyze")
async def analyze_compat(payload: dict, db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    msg = str(payload.get("query") or payload.get("message") or "").strip() or "hi"
    service = LensEngineService(db)
    return {"reply": await service.chat(msg)}
