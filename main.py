from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv
from sqlmodel import SQLModel, Field, Session, select, create_engine, or_
from sqlalchemy import func, distinct, desc, asc
import os
import requests
import csv
import io
import base64
import random
from requests.auth import HTTPBasicAuth
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, date
from groq import Groq

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False) if DATABASE_URL else create_engine("sqlite:///./evidlens.db", connect_args={"check_same_thread": False})

app = FastAPI(title="EvidLens API", version="2.5.2")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PRICING = {"BASIC": {"monthly": 500, "yearly": 5000},"PROFESSIONAL": {"monthly": 1500, "yearly": 15000},"ENTERPRISE": {"monthly": 5000, "yearly": 50000}}
ADDONS = {"EXTRA_REPORTS_10": {"name": "10 Extra Reports", "one_time": 1000},"API_ACCESS": {"name": "API Access", "monthly": 2000},"TEAM_SEAT": {"name": "Extra Team Seat", "monthly": 500},"DATA_EXPORT": {"name": "Bulk Data Export", "one_time": 5000}}
ALC = {"CUSTOM_REPORT": {"name": "Custom Market Report", "price": 25000},"DATA_ONBOARDING": {"name": "Data Onboarding", "price": 50000},"TRAINING": {"name": "Team Training", "price": 15000}}

def get_mpesa_token():
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(api_url, auth=HTTPBasicAuth(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return r.json()["access_token"]
def get_timestamp(): return datetime.now().strftime('%Y%m%d%H%M%S')
def get_password(shortcode, passkey, timestamp): return base64.b64encode((shortcode + passkey + timestamp).encode()).decode('utf-8')

class Subscription(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); user_id: int; plan: str; status: str; expires_at: datetime; mpesa_receipt: str = None
class QueryLog(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); user_id: int; date: date
class MpesaTransaction(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); user_id: int; phone: str; amount: float; receipt: str; checkout_id: str; plan: str; status: str; created_at: datetime = Field(default_factory=datetime.utcnow)
class Sector(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); name: str = Field(unique=True)
class County(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); name: str = Field(unique=True)
class SubCounty(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); name: str; county_id: int = Field(foreign_key="county.id")
class FMCGProduct(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); name: str = Field(unique=True); category: str
class Company(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); name: str; sector: str; county: str; subcounty: str = None; rating: float = 0; reviews: int = 0; address: str; lat: float; lng: float
class MarketMetric(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); product_name: str; sector: str; county: str; subcounty: str = "All"; demand_score: int; market_size_kes: float; growth_percent: float; volume: int; opportunity_score: float = 0
class MarketSearch(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); query: str; sector: str; county: str; score: int; created_at: datetime = Field(default_factory=datetime.utcnow)
class SocialPost(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); platform: str; post_id: str; text: str; author: str; created_at: datetime; keywords: str; sentiment: str = "neutral"; created_at_db: datetime = Field(default_factory=datetime.utcnow)
class MarketPrice(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); product: str; price: float; county: str; market: str; source: str = "AIT"; fetched_at: datetime = Field(default_factory=datetime.utcnow)
class NewsArticle(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True); title: str; url: str; source: str; published_at: datetime; summary: str; keywords: str; fetched_at: datetime = Field(default_factory=datetime.utcnow)

AT_API_KEY = os.getenv("AT_API_KEY"); AT_USERNAME = os.getenv("AT_USERNAME"); NEWS_API_KEY = os.getenv("NEWS_API_KEY"); RESEND_API_KEY = os.getenv("RESEND_API_KEY"); X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN"); GROQ_API_KEY = os.getenv("GROQ_API_KEY"); MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL"); MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY"); MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET"); MPESA_ENV = os.getenv("MPESA_ENV", "sandbox"); MPESA_PASSKEY = os.getenv("MPESA_PASSKEY"); MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")

def get_session():
    db = Session(engine)
    try: yield db
    finally: db.close()
def get_db():
    db = Session(engine)
    try: yield db
    finally: db.close()
def get_current_user(request: Request, session: Session = Depends(get_session)):
    user_id = request.cookies.get("user_id") or 1
    return int(user_id)
def get_subscription(db: Session, user_id: int): return db.exec(select(Subscription).where(Subscription.user_id == user_id)).first()
def get_queries_today(db: Session, user_id: int): return len(db.exec(select(QueryLog).where(QueryLog.user_id == user_id, QueryLog.date == date.today())).all())
def log_query(db: Session, user_id: int): db.add(QueryLog(user_id=user_id, date=date.today())); db.commit()
def check_subscription(user_id: int, db: Session):
    sub = get_subscription(db, user_id)
    if not sub or sub.status!= "active" or sub.expires_at < datetime.utcnow():
        if get_queries_today(db, user_id) >= 3: raise HTTPException(status_code=402, detail="Subscribe to continue. 3 free queries used.")
    return True

def seed_data(db: Session):
    if db.exec(select(Sector)).first(): return
    sectors = ["Agriculture","Livestock","Dairy","Poultry","Fisheries & Aquaculture","Forestry","Horticulture","Floriculture","Tea","Coffee","Sugar","Cotton","Mining","Oil & Gas","Quarrying","Manufacturing","Food Processing","Beverage Production","Textile & Apparel","Leather & Footwear","Furniture","Paper & Packaging","Printing & Publishing","Chemicals","Pharmaceuticals","Plastics & Rubber","Metal & Steel","Cement","Glass & Ceramics","Construction","Building Materials","Real Estate","Property Management","Architecture","Engineering Services","Energy","Renewable Energy","Electricity Supply","Water & Sanitation","Waste Management & Recycling","Wholesale Trade","Retail Trade","E-commerce","Automotive","Vehicle Assembly","Vehicle Sales","Vehicle Repair & Maintenance","Logistics","Transportation","Warehousing","Courier & Postal Services","Aviation","Maritime & Shipping","Rail Transport","Hospitality","Tourism","Travel Agencies","Restaurants & Catering","Financial Services","Banking","Insurance","SACCOs","Microfinance","FinTech","Information & Communication Technology (ICT)","Telecommunications","Software Development","Cybersecurity","Media & Broadcasting","Advertising & Marketing","Education & Training","Healthcare","Professional & Consulting Services","Public Administration & Government","NGOs, International Organizations & Development Partners"]
    for s in sectors: db.add(Sector(name=s))
    counties_subs = {"Mombasa County": ["Changamwe", "Jomvu", "Kisauni", "Nyali", "Likoni", "Mvita"],"Kwale County": ["Msambweni", "Lunga Lunga", "Matuga", "Kinango"],"Kilifi County": ["Kilifi North", "Kilifi South", "Kaloleni", "Rabai", "Ganze", "Malindi", "Magarini"],"Tana River County": ["Garsen", "Galole", "Bura"],"Lamu County": ["Lamu East", "Lamu West"],"Taita-Taveta County": ["Taveta", "Wundanyi", "Mwatate", "Voi"],"Garissa County": ["Garissa Township", "Balambala", "Lagdera", "Dadaab", "Fafi", "Ijara"],"Wajir County": ["Wajir North", "Wajir East", "Tarbaj", "Wajir West", "Eldas", "Wajir South"],"Mandera County": ["Mandera West", "Banissa", "Mandera North", "Mandera South", "Mandera East", "Lafey"],"Marsabit County": ["Moyale", "North Horr", "Saku", "Laisamis"],"Isiolo County": ["Isiolo North", "Isiolo South"],"Meru County": ["Igembe South", "Igembe Central", "Igembe North", "Tigania West", "Tigania East", "North Imenti", "Buuri", "Central Imenti", "South Imenti"],"Tharaka-Nithi County": ["Maara", "Chuka/Igambang'ombe", "Tharaka"],"Embu County": ["Manyatta", "Runyenjes", "Mbeere South", "Mbeere North"],"Kitui County": ["Mwingi North", "Mwingi West", "Mwingi Central", "Kitui West", "Kitui Rural", "Kitui Central", "Kitui East", "Kitui South"],"Machakos County": ["Masinga", "Yatta", "Kangundo", "Matungulu", "Kathiani", "Mavoko", "Machakos Town", "Mwala"],"Makueni County": ["Mbooni", "Kilome", "Kaiti", "Makueni", "Kibwezi West", "Kibwezi East"],"Nyandarua County": ["Kinangop", "Kipipiri", "Ol Kalou", "Ol Jorok", "Ndaragwa"],"Nyeri County": ["Tetu", "Kieni East", "Kieni West", "Mathira East", "Mathira West", "Othaya", "Mukurweini", "Nyeri Central"],"Kirinyaga County": ["Mwea East", "Mwea West", "Gichugu", "Ndia", "Kirinyaga Central"],"Murang'a County": ["Kangema", "Mathioya", "Kiharu", "Kigumo", "Maragwa", "Kandara", "Gatanga"],"Kiambu County": ["Gatundu South", "Gatundu North", "Juja", "Thika Town", "Ruiru", "Githunguri", "Kiambu", "Kiambaa", "Kabete", "Kikuyu", "Limuru", "Lari"],"Turkana County": ["Turkana North", "Turkana West", "Turkana Central", "Loima", "Turkana South", "Turkana East"],"West Pokot County": ["Kapenguria", "Sigor", "Kacheliba", "Pokot South"],"Samburu County": ["Samburu West", "Samburu North", "Samburu East"],"Trans Nzoia County": ["Kwanza", "Endebess", "Saboti", "Kiminini", "Cherangany"],"Uasin Gishu County": ["Soy", "Turbo", "Moiben", "Ainabkoi", "Kapseret", "Kesses"],"Elgeyo-Marakwet County": ["Marakwet East", "Marakwet West", "Keiyo North", "Keiyo South"],"Nandi County": ["Tinderet", "Aldai", "Nandi Hills", "Chesumei", "Emgwen", "Mosop"],"Baringo County": ["Tiaty", "Baringo North", "Baringo Central", "Baringo South", "Mogotio", "Eldama Ravine"],"Laikipia County": ["Laikipia West", "Laikipia East", "Laikipia North"],"Nakuru County": ["Molo", "Njoro", "Naivasha", "Gilgil", "Kuresoi South", "Kuresoi North", "Subukia", "Rongai", "Bahati", "Nakuru Town West", "Nakuru Town East"],"Narok County": ["Kilgoris", "Emurua Dikirr", "Narok North", "Narok East", "Narok South", "Narok West"],"Kajiado County": ["Kajiado North", "Kajiado Central", "Kajiado East", "Kajiado West", "Kajiado South"],"Kericho County": ["Kipkelion East", "Kipkelion West", "Ainamoi", "Bureti", "Belgut", "Sigowet/Soin"],"Bomet County": ["Sotik", "Chepalungu", "Bomet East", "Bomet Central", "Konoin"],"Kakamega County": ["Lugari", "Likuyani", "Malava", "Lurambi", "Navakholo", "Mumias West", "Mumias East", "Matungu", "Butere", "Khwisero", "Shinyalu", "Ikolomani"],"Vihiga County": ["Vihiga", "Sabatia", "Hamisi", "Luanda", "Emuhaya"],"Bungoma County": ["Mt. Elgon", "Sirisia", "Kabuchai", "Bumula", "Kanduyi", "Webuye East", "Webuye West", "Kimilili", "Tongaren"],"Busia County": ["Teso North", "Teso South", "Nambale", "Matayos", "Butula", "Funyula", "Budalangi"],"Siaya County": ["Ugenya", "Ugunja", "Alego Usonga", "Gem", "Bondo", "Rarieda"],"Kisumu County": ["Kisumu East", "Kisumu West", "Kisumu Central", "Seme", "Nyando", "Muhoroni", "Nyakach"],"Homa Bay County": ["Kasipul", "Kabondo Kasipul", "Karachuonyo", "Rangwe", "Homa Bay Town", "Ndhiwa", "Mbita", "Suba"],"Migori County": ["Rongo", "Awendo", "Suna East", "Suna West", "Uriri", "Nyatike", "Kuria West", "Kuria East"],"Kisii County": ["Bonchari", "South Mugirango", "Bomachoge Borabu", "Bobasi", "Bomachoge Chache", "Nyaribari Masaba", "Nyaribari Chache", "Kitutu Chache North", "Kitutu Chache South"],"Nyamira County": ["Kitutu Masaba", "West Mugirango", "North Mugirango", "Borabu"],"Nairobi County": ["Westlands", "Dagoretti North", "Dagoretti South", "Lang'ata", "Kibra", "Roysambu", "Kasarani", "Ruaraka", "Embakasi South", "Embakasi North", "Embakasi Central", "Embakasi East", "Embakasi West", "Makadara", "Kamukunji", "Starehe", "Mathare"]}
    for county, subs in counties_subs.items():
        c = County(name=county); db.add(c); db.commit(); db.refresh(c)
        for sub in subs: db.add(SubCounty(name=sub, county_id=c.id))
    fmcg = ["Maize flour","Wheat flour","Rice","Pasta","Spaghetti","Macaroni","Noodles","Semolina","Sorghum flour","Millet flour","Cassava flour","Porridge flour","Bread","Buns","Cakes","Biscuits","Crackers","Cookies","Breakfast cereals","Oats","Cornflakes","Muesli","Granola","Pancake mix","Baking flour","Baking powder","Yeast","Cooking oil","Margarine","Butter","Ghee","Shortening","Salt","Sugar","Brown sugar","Honey","Syrup","Vinegar","Soy sauce","Tomato paste","Tomato sauce","Ketchup","Mayonnaise","Mustard","Chilli sauce","Hot sauce","BBQ sauce","Salad dressing","Stock cubes","Seasoning cubes","Curry powder","Black pepper","Mixed spices","Cinnamon","Turmeric","Ginger powder","Garlic powder","Paprika","Herbs","Fresh milk","UHT milk","Flavoured milk","Yoghurt","Drinking yoghurt","Cheese","Cream","Sour cream","Whipping cream","Ice cream","Condensed milk","Evaporated milk","Milk powder","Bottled water","Mineral water","Soft drinks","Cola","Orange soda","Lemon soda","Energy drinks","Sports drinks","Fruit juice","Juice concentrates","Tea","Coffee","Instant coffee","Coffee creamer","Cocoa","Drinking chocolate","Iced tea","Malt drinks","Potato crisps","Tortilla chips","Popcorn","Peanuts","Cashew nuts","Mixed nuts","Raisins","Dried fruits","Chocolate","Chocolate bars","Candy","Sweets","Chewing gum","Mints","Lollipops","Toffees","Wafer biscuits","Baby diapers","Baby wipes","Baby lotion","Baby oil","Baby powder","Baby shampoo","Baby soap","Baby toothpaste","Baby food","Infant formula","Baby cereal","Bath soap","Beauty soap","Liquid soap","Hand wash","Shower gel","Body wash","Shampoo","Conditioner","Hair oil","Hair cream","Hair gel","Hair spray","Hair dye","Body lotion","Body cream","Petroleum jelly","Face cream","Face wash","Facial scrub","Moisturizer","Sunscreen","Lip balm","Lipstick","Face powder","Foundation","Mascara","Eyeliner","Nail polish","Nail polish remover","Deodorant","Antiperspirant","Perfume","Body spray","Cologne","Aftershave","Shaving cream","Shaving gel","Razors","Toothpaste","Toothbrush","Mouthwash","Dental floss","Cotton buds","Cotton wool","Wet wipes","Sanitary pads","Tampons","Panty liners","Adult diapers","Toilet paper","Facial tissues","Laundry detergent powder","Liquid laundry detergent","Fabric softener","Bleach","Stain remover","Laundry bar soap","Dishwashing liquid","Dishwasher tablets","Multipurpose cleaner","Floor cleaner","Toilet cleaner","Glass cleaner","Kitchen cleaner","Bathroom cleaner","Disinfectant","Air freshener","Furniture polish","Metal polish","Scouring powder","Drain cleaner","Aluminium foil","Cling film","Baking paper","Garbage bags","Paper towels","Napkins","Disposable plates","Disposable cups","Disposable cutlery","Food storage bags","Matches","Lighters","Candles","Charcoal","Fire starters","Mosquito spray","Mosquito coils","Mosquito repellent","Insecticide spray","Cockroach killer","Ant killer","Fly spray","Rat poison","Rat traps","Dog food","Cat food","Bird food","Fish food","Pet shampoo","Pet treats","Cat litter","Pain relievers","Cough syrup","Lozenges","Antacids","Oral rehydration salts","Antiseptic liquid","Antiseptic cream","Hand sanitizer","First aid plasters","Bandages","Thermometer","Vitamins","Mineral supplements","Nutrition supplements","Frozen vegetables","Frozen fruits","Frozen chips","Frozen pizza","Frozen chicken","Frozen fish","Frozen sausages","Frozen burgers","Frozen pastries","Baked beans","Canned tomatoes","Canned vegetables","Canned fruits","Canned fish","Canned meat","Soup","Instant soup","Instant noodles","Ready meals","Ready-to-eat cereals","Peanut butter","Chocolate spread","Jam","Marmalade","Fruit preserves","Tahini"]
    for p in fmcg: db.add(FMCGProduct(name=p, category="FMCG"))
    db.commit()

def generate_insights(user_message: str):
    try:
        completion = client.chat.completions.create(model="llama-3.3-70b-versatile",messages=[{"role": "system", "content": "You are EvidLens AI. You give market insights for Kenyan farmers and SMEs. Be concise and data-driven. Use KES and Counties."},{"role": "user", "content": user_message}],)
        return completion.choices[0].message.content
    except Exception as e: return f"AI Error: {str(e)}. Please try again."

from app.modules.db import init_db
from app.modules.cron.price_cron import start_scheduler
scheduler = AsyncIOScheduler()
@app.on_event("startup")
async def on_startup():
    init_db(); SQLModel.metadata.create_all(engine); db = Session(engine); seed_data(db); db.close(); start_scheduler(); scheduler.add_job(lambda: None, "interval", hours=1); scheduler.start()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

@app.post("/chat")
async def chat(payload: dict, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    check_subscription(user_id, db); db.add(MarketSearch(query=payload["message"], sector="All", county="Kenya", score=random.randint(50,100))); db.commit(); ai_response = generate_insights(payload["message"]); log_query(db, user_id); return {"response": ai_response}

def apply_sort(q, model, sort_by: str, order: str):
    if not sort_by or not hasattr(model, sort_by): return q
    col = getattr(model, sort_by)
    return q.order_by(desc(col) if order == "desc" else asc(col))

@app.get("/api/sectors")
def get_sectors(search: str = "", session: Session = Depends(get_session)):
    q = select(Sector)
    if search: q = q.where(Sector.name.contains(search))
    return {"sectors": [s.name for s in session.exec(q).all()]}

@app.get("/api/counties")
def get_counties(search: str = "", session: Session = Depends(get_session)):
    q = select(County)
    if search: q = q.where(County.name.contains(search))
    return {"counties": [c.name for c in session.exec(q).all()]}

@app.get("/api/subcounties")
def get_subcounties(county: str = "", search: str = "", session: Session = Depends(get_session)):
    q = select(SubCounty)
    if county: q = q.join(County).where(County.name == county)
    if search: q = q.where(SubCounty.name.contains(search))
    return {"subcounties": [s.name for s in session.exec(q).all()]}

@app.get("/api/products")
def get_products(search: str = "", session: Session = Depends(get_session)):
    q = select(FMCGProduct)
    if search: q = q.where(FMCGProduct.name.contains(search))
    return {"products": [p.name for p in session.exec(q).all()]}

@app.get("/api/companies")
def get_companies(search: str = "", sector: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "rating", order: str = "desc", session: Session = Depends(get_session)):
    q = select(Company)
    if search: q = q.where(or_(Company.name.contains(search), Company.sector.contains(search), Company.county.contains(search)))
    if sector: q = q.where(Company.sector == sector)
    if county: q = q.where(Company.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, Company, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"companies": [c.dict() for c in data], "total": total, "page": page}

@app.get("/api/prices")
def get_prices(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "price", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketPrice)
    if search: q = q.where(or_(MarketPrice.product.contains(search), MarketPrice.county.contains(search)))
    if product: q = q.where(MarketPrice.product == product)
    if county: q = q.where(MarketPrice.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketPrice, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"prices": [p.dict() for p in data], "total": total, "page": page}

@app.get("/api/demand")
def get_demand(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "demand_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product_name.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product_name == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"demand": [m.dict() for m in data], "total": total, "page": page}

@app.get("/api/county-stats")
def get_county_stats(search: str = "", page: int = 1, limit: int = 47, sort_by: str = "market_size", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric.county,func.sum(MarketMetric.market_size_kes).label("market_size"),func.avg(MarketMetric.growth_percent).label("growth"),func.sum(MarketMetric.volume).label("volume")).group_by(MarketMetric.county)
    if search: q = q.where(MarketMetric.county.contains(search))
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    stats = [dict(r._mapping) for r in data]
    stats.sort(key=lambda x: x.get(sort_by, 0), reverse=(order=="desc"))
    return {"stats": stats, "total": 47, "page": page}

@app.get("/api/top-sectors")
def get_top_sectors(search: str = "", page: int = 1, limit: int = 10, session: Session = Depends(get_session)):
    q = select(MarketSearch.sector, func.count(MarketSearch.id).label("count")).group_by(MarketSearch.sector)
    if search: q = q.where(MarketSearch.sector.contains(search))
    total = len(session.exec(q).all())
    data = session.exec(q.order_by(func.count(MarketSearch.id).desc()).offset((page-1)*limit).limit(limit)).all()
    return {"sectors": [dict(r._mapping) for r in data], "total": total, "page": page}

@app.get("/api/opportunities")
def get_opportunities(search: str = "", product: str = "", county: str = "", page: int = 1, limit: int = 10, sort_by: str = "opportunity_score", order: str = "desc", session: Session = Depends(get_session)):
    q = select(MarketMetric)
    if search: q = q.where(or_(MarketMetric.product_name.contains(search), MarketMetric.county.contains(search)))
    if product: q = q.where(MarketMetric.product_name == product)
    if county: q = q.where(MarketMetric.county == county)
    total = len(session.exec(q).all())
    q = apply_sort(q, MarketMetric, sort_by, order)
    data = session.exec(q.offset((page-1)*limit).limit(limit)).all()
    return {"opportunities": [m.dict() for m in data], "total": total, "page": page}

@app.get("/api/export/{table}")
def export_csv(table: str, search: str = "", session: Session = Depends(get_session)):
    output = io.StringIO(); writer = csv.writer(output)
    if table == "companies": q = select(Company); data = session.exec(q).all(); writer.writerow(["Name","Sector","County","Rating","Reviews","Address","Lat","Lng"]); [writer.writerow([r.name,r.sector,r.county,r.rating,r.reviews,r.address,r.lat,r.lng]) for r in data]
    elif table == "prices": q = select(MarketPrice); data = session.exec(q).all(); writer.writerow(["Product","Price","County","Market","Source","FetchedAt"]); [writer.writerow([r.product,r.price,r.county,r.market,r.source,r.fetched_at]) for r in data]
    elif table == "demand": q = select(MarketMetric); data = session.exec(q).all(); writer.writerow(["Product","Sector","County","DemandScore","MarketSizeKES","Growth%","Volume","OpportunityScore"]); [writer.writerow([r.product_name,r.sector,r.county,r.demand_score,r.market_size_kes,r.growth_percent,r.volume,r.opportunity_score]) for r in data]
    output.seek(0); return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=evidlens_{table}.csv"})

@app.get("/api/social-feed")
def get_social_feed(platform: str = "all", session: Session = Depends(get_session)):
    q = select(SocialPost).order_by(SocialPost.created_at.desc()).limit(20)
    if platform!= "all": q = q.where(SocialPost.platform == platform)
    return {"posts": [p.dict() for p in session.exec(q).all()]}

@app.get("/api/news-feed")
def get_news_feed(session: Session = Depends(get_session)):
    return {"articles": [n.dict() for n in session.exec(select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(20)).all()]}

@app.get("/api/dashboard")
def dashboard_api(session: Session = Depends(get_session)):
    stats = {"insights_generated": session.exec(select(MarketSearch)).count(),"sectors_covered": session.exec(select(Sector)).count(),"reports_exported": session.exec(select(Subscription)).count(),"active_products": session.exec(select(FMCGProduct)).count()}
    top_demand = session.exec(select(MarketMetric).order_by(desc(MarketMetric.demand_score)).limit(1)).first()
    trending = {"category": top_demand.sector if top_demand else "Agriculture","headline": f"{top_demand.product_name} demand up in {top_demand.county}" if top_demand else "No data yet"}
    modules = [{"name": "Competitive Engine","icon": "🎯","insights": session.exec(select(Company)).count(),"growth": "+8%","status": "LIVE","url": "#"},{"name": "Price Oracle","icon": "💰","insights": session.exec(select(MarketPrice)).count(),"growth": "+15%","status": "LIVE","url": "#"},{"name": "Demand Radar","icon": "📈","insights": session.exec(select(MarketMetric)).count(),"growth": "+22%","status": "LIVE","url": "#"},{"name": "County Mapper","icon": "🗺️","insights": session.exec(select(County)).count(),"growth": "+5%","status": "LIVE","url": "#"},{"name": "Consumer Pulse","icon": "📊","insights": session.exec(select(SocialPost)).count(),"growth": "+18%","status": "LIVE","url": "#"},{"name": "Risk Sentinel","icon": "⚠️","insights": session.exec(select(NewsArticle)).count(),"growth": "+12%","status": "LIVE","url": "#"}]
    return {"stats": stats,"trending": trending,"modules": modules,"last_updated": datetime.utcnow().isoformat()}

@app.get("/api/pricing")
def api_pricing(): return {"plans": PRICING,"addons": ADDONS,"alc": ALC}

@app.post("/api/checkout")
def mpesa_stk_push(payload: dict, user_id: int = Depends(get_current_user)):
    plan = payload.get("plan"); billing = payload.get("billing"); phone = payload.get("phone"); amount = PRICING[plan][billing]; token = get_mpesa_token(); timestamp = get_timestamp(); password = get_password(MPESA_SHORTCODE, MPESA_PASSKEY, timestamp); api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"; headers = {"Authorization": "Bearer " + token}; payload_mpesa = {"BusinessShortCode": MPESA_SHORTCODE,"Password": password,"Timestamp": timestamp,"TransactionType": "CustomerPayBillOnline","Amount": amount,"PartyA": phone,"PartyB": MPESA_SHORTCODE,"PhoneNumber": phone,"CallBackURL": MPESA_CALLBACK_URL,"AccountReference": f"EvidLens-{plan}-{user_id}","TransactionDesc": f"{plan} {billing} Subscription"}; r = requests.post(api_url, json=payload_mpesa, headers=headers); return r.json()

@app.post("/api/mpesa-callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        stk = data["Body"]["stkCallback"]
        if stk["ResultCode"] == 0:
            items = {i["Name"]: i["Value"] for i in stk["CallbackMetadata"]["Item"]}; account_ref = items["AccountReference"]; plan = account_ref.split("-")[1]; user_id = int(account_ref.split("-")[2]); expires = datetime.utcnow() + timedelta(days=30); sub = get_subscription(db, user_id)
            if sub: sub.plan = plan; sub.status = "active"; sub.expires_at = expires; sub.mpesa_receipt = items["MpesaReceiptNumber"]
            else: db.add(Subscription(user_id=user_id, plan=plan, status="active", expires_at=expires, mpesa_receipt=items["MpesaReceiptNumber"]))
            db.add(MpesaTransaction(user_id=user_id, phone=items["PhoneNumber"], amount=items["Amount"], receipt=items["MpesaReceiptNumber"], checkout_id=stk["CheckoutRequestID"], plan=plan, status="SUCCESS")); db.commit()
    except Exception as e: print("Callback Error:", e)
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@app.get("/health")
def health(): return {"status": "healthy", "version": "2.5.2"}
@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request): return templates.TemplateResponse("pricing.html", {"request": request, "plans": PRICING, "addons": ADDONS, "alc": ALC})
@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request): return templates.TemplateResponse("privacy.html", {"request": request})
@app.get("/terms", response_class=
@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request): return templates.TemplateResponse("terms.html", {"request": request})
@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request): return templates.TemplateResponse("contact.html", {"request": request})
@app.get("/about", response_class=HTMLResponse)
def about(request: Request): return templates.TemplateResponse("about.html", {"request": request})
@app.get("/undefined")
def catch_undefined(): return {"status": "ignored"}
@app.get("/", response_class=HTMLResponse)
async def root(request: Request): return templates.TemplateResponse("dashboard.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
