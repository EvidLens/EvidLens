from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, desc, or_
import io, csv

from app.modules.core.db import get_session
from app.modules.core.models import MarketMetric, KenyaLensBusiness, NewsArticle, SocialMention, ExportOpportunity, User, Subscription, UserSubscription
from app.modules.auth.dependencies import get_current_user
from app.modules.lens_engine.service import LensEngineService, scrape_kpin_prices, fetch_real_news, fetch_real_tweets
from app.core.service import _core
from app.modules.payments.mpesa import get_daraja_token, get_timestamp, get_password

router = APIRouter()

PRICING = _core.PRICING
ADDONS = _core.ADDONS
ALC = _core.ALC
MPESA_ENV = _core.MPESA_ENV
DARAJA_SHORTCODE = _core.MPESA_SHORTCODE
DARAJA_PASSKEY = _core.MPESA_PASSKEY
MPESA_CALLBACK_URL = _core.MPESA_CALLBACK_URL

def apply_sort(query, model, sort_by, order):
    column = getattr(model, sort_by, model.id)
    if order == "desc":
        return query.order_by(desc(column))
    return query.order_by(column)

@router.get("/api/market/risk")
def risk_sentinel_api(session: Session = Depends(get_session)):
    news = session.exec(select(NewsArticle.id, NewsArticle.title, NewsArticle.category, NewsArticle.summary, NewsArticle.published_at).order_by(NewsArticle.published_at.desc()).limit(10)).all()
    return {"risk_alerts": [dict(n._mapping) for n in news]}

@router.get("/api/market/export")
def export_navigator_api(session: Session = Depends(get_session)):
    exports = session.exec(select(ExportOpportunity).limit(20)).all()
    return {"export_opportunities": [e.dict() for e in exports]}

@router.get("/api/sectors")
def get_sectors(search: str = "", session: Session = Depends(get_session)):
    q = select(func.distinct(MarketMetric.sector))
    if search: q = q.where(MarketMetric.sector.contains(search))
    return {"sectors": [s[0] for s in session.exec(q).all() if s[0]]}

@router.get("/api/counties")
def get_counties(search: str = "", session: Session = Depends(get_session)):
    q = select(func.distinct(MarketMetric.county))
    if search: q = q.where(MarketMetric.county.contains(search))
    return {"counties": [c[0] for c in session.exec(q).all() if c[0]]}

@router.get("/api/subcounties")
def get_subcounties(county: str = "", search: str = "", session: Session = Depends(get_session)):
    return {"subcounties": []}

@router.get("/api/products")
def get_products(search: str = "", session: Session = Depends(get_session)):
    q = select(func.distinct(MarketMetric.product))
    if search: q = q.where(MarketMetric.product.contains(search))
    return {"products": [p[0] for p in session.exec(q).all() if p[0]]}

@router.get("/api/companies")
def get_companies(search: str = "", sector: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "id", order: str = "desc", session: Session = Depends(get_session)):
    q = select(KenyaLensBusiness)
    if search: q = q.where(or_(KenyaLensBusiness.name.ilike(f"%{search}%"), KenyaLensBusiness.sector.ilike(f"%{search}%"), KenyaLensBusiness.county.ilike(f"%{search}%")))
    if sector: q = q.where(KenyaLensBusiness.sector == sector)
    if county: q = q.where(KenyaLensBusiness.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, KenyaLensBusiness, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": [c.dict() for c in data], "total": total, "page": page}

@router.get("/api/prices")
def get_prices(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "avg_price_kes", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"prices": [p.dict() for p in data], "total": total, "page": page}

@router.get("/api/demand")
def get_demand(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"demand": [m.dict() for m in data], "total": total, "page": page}

@router.get("/api/county-stats")
def get_county_stats(search: str = "", page: int = 1, limit: int = 47, sort_by: str = "market_size", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric.county, func.sum(MarketMetric.avg_price_kes).label("market_size"), func.avg(MarketMetric.demand_score).label("growth"), func.count(MarketMetric.id).label("volume")).group_by(MarketMetric.county)
    if search: q = q.where(MarketMetric.county.contains(search))
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    stats = [dict(r._mapping) for r in data]
    stats.sort(key=lambda x: x.get(sort_by, 0), reverse=(order=="desc"))
    return {"stats": stats, "total": 47, "page": page}

@router.get("/api/top-sectors")
def get_top_sectors(search: str = "", page: int = 1, limit: int = 10, session: Session = Depends(get_session)):
    q = select(MarketMetric.sector, func.count(MarketMetric.id).label("count")).group_by(MarketMetric.sector)
    if search: q = q.where(MarketMetric.sector.contains(search))
    total = len(session.exec(q).all())
    data = session.exec(q.order_by(func.count(MarketMetric.id).desc()).offset((page-1)*limit).limit(limit)).all()
    return {"sectors": [dict(r._mapping) for r in data], "total": total, "page": page}

@router.get("/api/opportunities")
def get_opportunities(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"opportunities": [m.dict() for m in data], "total": total, "page": page}

@router.get("/api/lens/insights")
async def get_lens_insights(sector: str = Query(...), county: str = None, db: Session = Depends(get_session)):
    service = LensEngineService(db)
    return await service.generate_sector_insights(sector, county)

@router.get("/api/export/{table}")
def export_csv(table: str, search: str = "", session: Session = Depends(get_session)):
    output = io.StringIO()
    writer = csv.writer(output)
    if table == "companies":
        q = select(KenyaLensBusiness)
        data = session.exec(q).all()
        writer.writerow(["Name","Sector","County","Rating","Reviews","Address","Lat","Lng"])
        [writer.writerow([r.name,r.sector,r.county,0,0,r.address or r.county,r.lat,r.lng]) for r in data]
    elif table == "prices":
        q = select(MarketMetric)
        data = session.exec(q).all()
        writer.writerow(["Product","Price","County","Market","Source","FetchedAt"])
        [writer.writerow([r.product,r.avg_price_kes,r.county,r.company_name or "","KPIN",r.created_at]) for r in data]
    elif table == "demand":
        q = select(MarketMetric)
        data = session.exec(q).all()
        writer.writerow(["Product","Sector","County","DemandScore","MarketSizeKES","Growth%","Volume","OpportunityScore"])
        [writer.writerow([r.product,r.sector,r.county,r.demand_score,r.avg_price_kes,0,0,0]) for r in data]
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"})

@router.get("/api/social-feed")
def get_social_feed(platform: str = "all", session: Session = Depends(get_session)):
    q = select(SocialMention).order_by(SocialMention.created_at.desc()).limit(20)
    if platform!= "all": q = q.where(SocialMention.platform == platform)
    return {"posts": [p.dict() for p in session.exec(q).all()]}

@router.get("/api/news-feed")
def get_news_feed(session: Session = Depends(get_session)):
    return {"articles": [n.dict() for n in session.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(20)).all()]}

@router.get("/api/pricing")
def api_pricing(): return {"plans": PRICING, "addons": ADDONS, "alc": ALC}

@router.post("/api/checkout")
def mpesa_stk_push(payload: dict, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    plan = payload.get("plan")
    billing = payload.get("billing")
    phone = payload.get("phone")
    price = PRICING[plan][billing]
    credits_map = {"BASIC": 10, "PROFESSIONAL": 100, "ENTERPRISE": 99999}
    token = get_daraja_token()
    timestamp = get_timestamp()
    password = get_password(DARAJA_SHORTCODE, DARAJA_PASSKEY, timestamp)
    api_url = ("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest")
    headers = {"Authorization": "Bearer " + token}
    payload_mpesa = {"BusinessShortCode": DARAJA_SHORTCODE,"Password": password,"Timestamp": timestamp,"TransactionType": "CustomerPayBillOnline","Amount": price,"PartyA": phone,"PartyB": DARAJA_SHORTCODE,"PhoneNumber": phone,"CallBackURL": MPESA_CALLBACK_URL,"AccountReference": f"EvidLens-{plan}-{user.id}","TransactionDesc": f"{plan} {billing} Subscription"}
    r = requests.post(api_url, json=payload_mpesa, headers=headers)
    session.add(Subscription(user_id=user.id, plan=plan, billing=billing, status="Pending", credits=credits_map[plan]))
    session.commit()
    return r.json()

@router.post("/api/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_session)):
    # keep only 1 version. delete the other duplicate
    data = await request.json()
    try:
        stk = data["Body"]["stkCallback"]
        if stk["ResultCode"] == 0:
            items = {i["Name"]: i["Value"] for i in stk["CallbackMetadata"]["Item"]}
            account_ref = items["AccountReference"]
            plan = account_ref.split("-")[1]
            user_id = int(account_ref.split("-")[2])
            expires = datetime.utcnow() + timedelta(days=30)
            sub = get_subscription(db, user_id)
            if sub:
                sub.plan = plan
                sub.status = "active"
                sub.expires_at = expires
            else:
                db.add(Subscription(user_id=user_id, plan=plan, billing="monthly", status="active", expires_at=expires, credits=PRICING[plan]["monthly"]))
            db.commit()
    except Exception: pass
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.post("/api/run-scraper")
def run_scraper():
    scrape_kpin_prices()
    fetch_real_news()
    fetch_real_tweets()
    return {"status": "scraper ran. DB updated with real prices"}

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
def catch_all(path: str):
    return {"status": "ok"}
