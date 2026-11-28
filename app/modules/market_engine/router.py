from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, desc
from datetime import datetime, timedelta, timezone
import logging, httpx, math, json
from pydantic import BaseModel

from app.core.db import get_session
from app.core.models import MarketMetric, NewsArticle, ExportOpportunity, Buyer, BuyerSearchCache, KeprobaRequest, SavedFair
from .buyer_finder import find_buyers

router = APIRouter(prefix="/market", tags=["Market"])
templates = Jinja2Templates(directory="app/templates")
UTC = timezone.utc
logger = logging.getLogger("evidlens.market")

HS_LIVE = {
 "tea": "090230", "black tea": "090230", "green tea": "090210", "tea extracts": "210120",
 "coffee": "090111", "coffee roasted": "090121", "coffee extracts": "210111", "coffee husks": "090190",
 "avocado": "080440", "avocados": "080440", "avocado oil": "151590",
 "flowers": "060319", "cut flowers": "060319", "roses": "060311", "carnations": "060312", "lilies": "060319", "orchids": "060313", "chrysanthemums": "060314", "flower buds": "060319",
 "macadamia": "080261", "macadamia nuts": "080261", "macadamia kernels": "080262",
 "pineapple": "080430", "pineapples": "080430", "pineapple juice": "200940", "canned pineapple": "200820",
 "mango": "080450", "mangoes": "080450", "mango juice": "200989", "dried mango": "080450",
 "french beans": "070820", "beans": "070820", "green beans": "070820", "runner beans": "070820", "snow peas": "070810", "sugar snap peas": "070810", "peas": "071310", "chickpeas": "071320", "lentils": "071340", "pigeon peas": "071360", "cowpeas": "071335", "kidney beans": "071333", "bambara nuts": "071333",
 "asparagus": "070920", "baby corn": "070990", "sweet corn": "071040", "sweetcorn": "071040",
 "cashew": "080131", "cashew nuts": "080131", "coconut": "080119", "coconuts": "080119", "coconut oil": "151319", "desiccated coconut": "080111",
 "honey": "040900", "beeswax": "152190",
 "tilapia": "030461", "fish": "030389", "nile perch": "030461", "tuna": "030341", "octopus": "030751", "prawns": "030617", "shrimp": "030617", "crab": "030614", "lobster": "030612", "dried fish": "030559", "smoked fish": "030549", "fish fillets": "030461",
 "maize": "100590", "maize flour": "110220", "wheat": "100199", "wheat flour": "110100", "rice": "100630", "sorghum": "100790", "millet": "100821", "barley": "100390", "oats": "100490",
 "sugar": "170199", "molasses": "170310", "raw sugar": "170111",
 "pyrethrum": "130219", "pyrethrum extracts": "130219",
 "vanilla": "090500", "vanilla extract": "130219",
 "sesame": "120740", "sesame seeds": "120740", "sesame oil": "151540",
 "fruit juice": "200989", "orange juice": "200911", "mango juice": "200989", "passion juice": "200989", "apple juice": "200971", "grape juice": "200961",
 "onions": "070310", "shallots": "070310", "garlic": "070320", "tomatoes": "070200", "tomato paste": "200290", "canned tomatoes": "200210",
 "oranges": "080510", "lemons": "080550", "limes": "080550", "grapefruit": "080540", "tangerines": "080521", "mandarins": "080521", "bananas": "080300", "plantains": "080300", "papaya": "080720", "pawpaw": "080720", "watermelon": "080711", "melon": "080719", "passion fruit": "081090", "passionfruit": "081090", "guava": "080450", "dragon fruit": "081090", "apples": "080810", "pears": "080830", "grapes": "080610", "strawberries": "081010", "raspberries": "081020", "blueberries": "081040",
 "potatoes": "070190", "sweet potatoes": "071420", "cassava": "071410", "yams": "071430", "arrow roots": "071490", "carrots": "070610", "cabbage": "070490", "kale": "070490", "sukuma wiki": "070490", "spinach": "070970", "lettuce": "070511", "broccoli": "070410", "cauliflower": "070410", "cucumber": "070700", "courgette": "070930", "zucchini": "070930", "eggplant": "070930", "aubergine": "070930", "bell pepper": "070960", "capsicum": "070960", "chillies": "070960", "chili": "070960", "hot pepper": "070960", "okra": "070999", "leeks": "070390", "celery": "070940", "mushrooms": "070951", "ginger": "091010", "turmeric": "091030", "chilli powder": "090421",
 "basil": "121190", "mint": "121190", "rosemary": "121190", "thyme": "091040", "chives": "070390", "parsley": "070999", "coriander": "070999", "dhania": "070999", "dill": "070999", "sage": "121190",
 "cotton": "520100", "cotton yarn": "520512", "cotton fabric": "520811", "sisal": "530500", "sisal fibre": "530500", "sisal twine": "560721", "wool": "510111", "silk": "500100", "jute": "530310",
 "t-shirts": "610910", "trousers": "620342", "shirts": "620520", "dresses": "620440", "skirts": "620450", "jackets": "620193", "sweaters": "611020", "underwear": "610711", "socks": "611595", "footwear": "640399", "leather shoes": "640399", "sandals": "640299", "bags": "420221", "handbags": "420221", "leather": "410799", "hides": "410120", "skins": "410210",
 "beef": "020130", "goat meat": "020450", "sheep meat": "020422", "mutton": "020422", "lamb": "020410", "pork": "020329", "chicken": "020712", "chicken meat": "020712", "eggs": "040721", "milk": "040110", "milk powder": "040210", "butter": "040510", "cheese": "040690", "yoghurt": "040310",
 "steel bars": "721420", "steel": "721420", "iron bars": "721420", "aluminium": "760110", "cement": "252310", "clinker": "252310", "glass": "700529", "plastics": "390110", "plastic bottles": "392330", "plastic bags": "392321", "paper": "480255", "cardboard": "480810", "soap": "340111", "detergent": "340250", "paint": "320890", "fertilizer": "310520", "pesticides": "380891", "medicines": "300490", "pharmaceuticals": "300490", "cosmetics": "330499", "essential oils": "330129", "tea tree oil": "330129", "perfume": "330300",
 "furniture": "940360", "wooden furniture": "940360", "wood": "440799", "timber": "440799", "plywood": "441231", "charcoal": "440200",
 "gold": "710812", "soda ash": "283620", "fluorspar": "252910", "salt": "250100", "limestone": "252100", "marble": "251511", "granite": "251611",
 "tobacco": "240110", "cigarettes": "240220", "beer": "220300", "wine": "220421", "spirits": "220830", "whisky": "220830", "vodka": "220860", "water": "220110", "mineral water": "220110", "soda": "220210", "soft drinks": "220210", "juice drinks": "220210",
 "animal feed": "230990", "pet food": "230910", "vegetable oil": "151190", "palm oil": "151190", "sunflower oil": "151211", "maize oil": "151521", "peanut butter": "200811", "groundnuts": "120242", "peanuts": "120242", "soya": "120190", "soybeans": "120190", "sunflower seeds": "120600", "castor seeds": "120730", "moringa": "121190",
 "cocoa": "180100", "chocolate": "180631", "sugar confectionery": "170490", "biscuits": "190531", "bread": "190590", "pasta": "190219", "noodles": "190230", "canned beans": "200551", "canned vegetables": "200599", "jam": "200799", "pickles": "200110",
 "machinery": "841981", "batteries": "850760", "cables": "854442", "tyres": "401110", "tires": "401110", "motor parts": "870899", "bicycles": "871200",
}
HS_NAMES = {"090230": "Black Tea", "090210": "Green Tea", "210120": "Tea extracts", "090111": "Coffee, not roasted", "090121": "Coffee, roasted", "210111": "Coffee extracts", "090190": "Coffee husks", "080440": "Avocados", "151590": "Avocado oil", "060319": "Cut Flowers", "060311": "Roses", "060312": "Carnations", "060313": "Orchids", "060314": "Chrysanthemums", "080261": "Macadamia nuts", "080262": "Macadamia kernels", "080430": "Pineapples", "200940": "Pineapple juice", "200820": "Canned pineapple", "080450": "Mangoes", "200989": "Fruit juices", "070820": "French Beans", "070810": "Snow peas", "071310": "Peas, dried", "071320": "Chickpeas", "071340": "Lentils", "071360": "Pigeon peas", "071335": "Cowpeas", "071333": "Kidney beans", "070920": "Asparagus", "070990": "Baby corn", "071040": "Sweet corn", "080131": "Cashew nuts", "080119": "Coconuts", "151319": "Coconut oil", "080111": "Desiccated coconut", "040900": "Natural Honey", "152190": "Beeswax", "030461": "Tilapia fillets", "030389": "Fish, frozen", "030341": "Tuna", "030751": "Octopus", "030617": "Prawns / shrimp", "030614": "Crab", "030612": "Lobster", "030559": "Dried fish", "030549": "Smoked fish", "100590": "Maize", "110220": "Maize flour", "100199": "Wheat", "110100": "Wheat flour", "100630": "Rice", "100790": "Sorghum", "100821": "Millet", "100390": "Barley", "100490": "Oats", "170199": "Cane Sugar", "170310": "Molasses", "170111": "Raw sugar", "130219": "Pyrethrum extracts", "090500": "Vanilla", "120740": "Sesame seeds", "151540": "Sesame oil", "200911": "Orange juice", "200971": "Apple juice", "200961": "Grape juice", "070310": "Onions", "070320": "Garlic", "070200": "Tomatoes", "200290": "Tomato paste", "200210": "Canned tomatoes", "080510": "Oranges", "080550": "Lemons / limes", "080540": "Grapefruit", "080521": "Tangerines", "080300": "Bananas", "080720": "Papaya", "080711": "Watermelon", "080719": "Melon", "081090": "Passion fruit", "080810": "Apples", "080830": "Pears", "080610": "Grapes", "081010": "Strawberries", "081020": "Raspberries", "081040": "Blueberries", "070190": "Potatoes", "071420": "Sweet potatoes", "071410": "Cassava", "071430": "Yams", "071490": "Arrow roots", "070610": "Carrots", "070490": "Cabbage / kale", "070970": "Spinach", "070511": "Lettuce", "070410": "Broccoli / cauliflower", "070700": "Cucumber", "070930": "Courgette / eggplant", "070960": "Peppers / chillies", "070999": "Okra / herbs", "070390": "Leeks / chives", "070940": "Celery", "070951": "Mushrooms", "091010": "Ginger", "091030": "Turmeric", "090421": "Chilli powder", "121190": "Herbs / moringa", "091040": "Thyme", "520100": "Cotton", "520512": "Cotton yarn", "520811": "Cotton fabric", "530500": "Sisal", "560721": "Sisal twine", "510111": "Wool", "500100": "Silk", "530310": "Jute", "610910": "T-shirts, cotton", "620342": "Trousers, cotton", "620520": "Shirts", "620440": "Dresses", "620450": "Skirts", "620193": "Jackets", "611020": "Sweaters", "610711": "Underwear", "611595": "Socks", "640399": "Footwear, leather", "640299": "Sandals", "420221": "Bags / handbags", "410799": "Leather", "410120": "Hides", "410210": "Skins", "020130": "Beef", "020450": "Goat meat", "020422": "Sheep meat", "020410": "Lamb", "020329": "Pork", "020712": "Chicken", "040721": "Eggs", "040110": "Milk", "040210": "Milk powder", "040510": "Butter", "040690": "Cheese", "040310": "Yoghurt", "721420": "Steel bars", "760110": "Aluminium", "252310": "Cement", "700529": "Glass", "390110": "Plastics", "392330": "Plastic bottles", "392321": "Plastic bags", "480255": "Paper", "480810": "Cardboard", "340111": "Soap", "340250": "Detergent", "320890": "Paint", "310520": "Fertilizer", "380891": "Pesticides", "300490": "Medicines", "330499": "Cosmetics", "330129": "Essential oils", "330300": "Perfume", "940360": "Wooden furniture", "440799": "Wood / timber", "441231": "Plywood", "440200": "Charcoal", "710812": "Gold", "283620": "Soda ash", "252910": "Fluorspar", "250100": "Salt", "252100": "Limestone", "251511": "Marble", "251611": "Granite", "240110": "Tobacco", "240220": "Cigarettes", "220300": "Beer", "220421": "Wine", "220830": "Spirits / whisky", "220860": "Vodka", "220110": "Water", "220210": "Soda / soft drinks", "230990": "Animal feed", "230910": "Pet food", "151190": "Vegetable / palm oil", "151211": "Sunflower oil", "151521": "Maize oil", "200811": "Peanut butter", "120242": "Groundnuts", "120190": "Soya", "120600": "Sunflower seeds", "120730": "Castor seeds", "180100": "Cocoa", "180631": "Chocolate", "170490": "Sugar confectionery", "190531": "Biscuits", "190590": "Bread", "190219": "Pasta", "190230": "Noodles", "200551": "Canned beans", "200599": "Canned vegetables", "200799": "Jam", "200110": "Pickles", "841981": "Machinery", "850760": "Batteries", "854442": "Cables", "401110": "Tyres", "870899": "Motor parts", "871200": "Bicycles"}

async def _get_user(request: Request, db: Session):
    try:
        from app.modules.auth.dependencies import get_current_user
        return await get_current_user(request, db)
    except Exception:
        return None

def _latest_per_product_county(rows):
    seen = {}
    for p in rows:
        key = ((getattr(p, 'product', '') or '').strip().lower(), (getattr(p, 'county', '') or '').strip().lower())
        if key not in seen:
            seen[key] = p
    return list(seen.values())

def _risk_level(title: str, category: str, summary: str) -> str:
    text = f"{title or ''} {category or ''} {summary or ''}".lower()
    if any(k in text for k in ["ban", "shutdown", "outbreak", "drought", "crisis", "sanction", "recall"]):
        return "HIGH"
    if any(k in text for k in ["deadline", "tax", "regulation", "rate hike", "shortage", "delay", "fine"]):
        return "MEDIUM"
    return "LOW"

def _fmt_date(dt):
    if not dt:
        return ""
    try:
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(dt)

def _comtrade_live(hs: str, year: int):
    try:
        with httpx.Client(timeout=30) as c:
            r = c.get("https://comtradeapi.un.org/public/v1/preview/C/A/HS", params={"reporterCode": "404", "period": str(year), "flowCode": "X", "partnerCode": "all", "partner2Code": "0", "customsCode": "C00", "motCode": "0", "breakdownMode": "classic", "includeDesc": "true", "cmdCode": hs})
            if r.status_code != 200:
                return {}, f"Comtrade {r.status_code}"
            out = {}
            for row in r.json().get("data", []):
                p = row.get("partnerDesc", "")
                if p in ("World", "Kenya", "", "Unspecified"):
                    continue
                out[p] = {"value": float(row.get("primaryValue") or 0), "qty": float(row.get("netWgt") or 0), "partner_code": row.get("partnerCode")}
            return out, None
    except Exception as e:
        return {}, str(e)

def _resolve_hs(q: str):
    if not q:
        return None
    p = q.lower().strip()
    if p in HS_LIVE:
        return HS_LIVE[p]
    for k, v in HS_LIVE.items():
        if p in k or k in p:
            return v
    return None

def _build_export_rows(q: str, country: str):
    hs = _resolve_hs(q)
    if not hs:
        return [], None, f"No HS code for '{q}'. Try: tea, coffee, avocado, flowers, macadamia, cotton", False
    d24, err = _comtrade_live(hs, 2024)
    d23, _ = _comtrade_live(hs, 2023)
    if err:
        return [], None, f"Comtrade failed: {err}. Try again in 1 min.", False
    if not d24:
        return [], None, "No Comtrade records for this HS in 2024. Kenya did not report exports for this HS in 2024, or data not yet published.", True
    prod_name = HS_NAMES.get(hs, q)
    exports = []
    for partner, d in d24.items():
        if country and country.lower() not in partner.lower():
            continue
        v24 = d["value"]
        v23 = d23.get(partner, {}).get("value", 0)
        growth = round((v24 - v23) / v23 * 100, 1) if v23 and v23 > 0 else None
        value_m = round(v24 / 1_000_000, 2)
        unit = round(v24 / d["qty"], 2) if d["qty"] else None
        size = max(0, min(100, (math.log10(max(value_m, 0.01) + 1) / 3.5) * 100))
        g_score = max(0, min(100, (growth + 20) / 50 * 100)) if growth is not None else 50
        score = round(size * 0.50 + g_score * 0.30 + 60 * 0.20)
        exports.append({
            "product": prod_name, "country": partner, "destination": partner,
            "partner": partner, "partnerDesc": partner, "partner_code": d.get("partner_code"),
            "opportunity_score": score, "score": score, "county": "Kenya",
            "value_m": value_m, "value": v24, "value_usd": v24, "primaryValue": v24,
            "qty": d["qty"], "quantity": d["qty"],
            "growth": growth, "unit_value": unit, "hs": hs,
            "year": 2024, "period": 2024, "source": "UN Comtrade",
        })
    exports = sorted(exports, key=lambda x: x["opportunity_score"], reverse=True)
    source = f"UN Comtrade Live 2024 + 2023 for growth - Kenya Reporter 404 - HS {hs} - https://comtradeapi.un.org"
    return exports, source, None, True

@router.get("/prices", response_class=HTMLResponse)
async def prices_page(request: Request, q: str = None, county: str = None, sector: str = None, db: Session = Depends(get_session)):
    prices = []
    try:
        rows = db.exec(select(MarketMetric).order_by(desc(MarketMetric.created_at)).limit(500)).all()
        rows = _latest_per_product_county(rows)
        for p in rows:
            if q and q.lower() not in (getattr(p, 'product', '') or '').lower():
                continue
            if county and county.lower() not in (getattr(p, 'county', '') or '').lower():
                continue
            if sector and sector.lower() not in (getattr(p, 'sector', '') or '').lower():
                continue
            price = getattr(p, 'avg_price_kes', None)
            demand = getattr(p, 'demand_score', None)
            created = getattr(p, 'created_at', '')
            prices.append({"product_name": getattr(p, 'product', 'Product') or 'Product', "product": getattr(p, 'product', 'Product') or 'Product', "county": getattr(p, 'county', 'Kenya') or 'Kenya', "sector": getattr(p, 'sector', 'Agriculture') or 'Agriculture', "price": price, "avg_price_kes": price, "demand_score": demand, "demand": demand, "created_at": created, "updated_at": created, "updated_label": _fmt_date(created), "source": "EvidLens Database"})
    except Exception as e:
        logger.exception(f"prices_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        prices = []
    current_user = await _get_user(request, db)
    return templates.TemplateResponse("market_prices.html", {"request": request, "prices": prices, "has_data": len(prices) > 0, "q": q or "", "county": county or "", "sector": sector or "", "current_user": current_user, "user": current_user})

@router.get("/demand", response_class=HTMLResponse)
async def demand_page(request: Request, db: Session = Depends(get_session)):
    demand = []
    try:
        rows = db.exec(select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score)).limit(100)).all()
        rows = _latest_per_product_county(rows)
        for d in rows:
            score = getattr(d, 'demand_score', None)
            if score is None:
                continue
            demand.append({"product": getattr(d, 'product', 'Product') or 'Product', "county": getattr(d, 'county', 'Kenya') or 'Kenya', "sector": getattr(d, 'sector', 'Agriculture') or 'Agriculture', "score": score, "demand_score": score, "price": getattr(d, 'avg_price_kes', None), "avg_price_kes": getattr(d, 'avg_price_kes', None), "source": "EvidLens Database"})
    except Exception as e:
        logger.exception(f"demand_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        demand = []
    current_user = await _get_user(request, db)
    return templates.TemplateResponse("market_demand.html", {"request": request, "demand": demand, "data": demand, "has_data": len(demand) > 0, "current_user": current_user, "user": current_user})

@router.get("/risk", response_class=HTMLResponse)
async def risk_page(request: Request, db: Session = Depends(get_session)):
    alerts = []
    try:
        since = datetime.now(UTC) - timedelta(days=14)
        rows = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
        for n in rows:
            title = getattr(n, 'title', 'Alert') or 'Alert'
            summary = getattr(n, 'summary', '') or ''
            if not summary or summary.strip().lower() == title.strip().lower():
                summary = getattr(n, 'category', '') or 'Market update - see source for details.'
            source = getattr(n, 'source', '') or 'EvidLens Database'
            if source.strip().lower() == "evidlens":
                source = "Curated by EvidLens"
            alerts.append({"title": title, "summary": summary, "source": source, "published_at": getattr(n, 'published_at', '') or '', "published_label": _fmt_date(getattr(n, 'published_at', None)), "category": getattr(n, 'category', '') or '', "level": _risk_level(title, getattr(n, 'category', ''), summary)})
    except Exception as e:
        logger.exception(f"risk_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        alerts = []
    current_user = await _get_user(request, db)
    return templates.TemplateResponse("market_risk.html", {"request": request, "risk_alerts": alerts, "alerts": alerts, "has_data": len(alerts) > 0, "current_user": current_user, "user": current_user})

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, q: str = None, country: str = None, county: str = None, db: Session = Depends(get_session)):
    q = (q or "").strip()
    country = (country or "").strip()
    county = (county or "").strip()
    exports = []
    error = None
    source = ""
    live = False
    if q:
        exports, source, error, live = _build_export_rows(q, country)
        if source is None:
            source = ""
    else:
        source = "Search a product to query UN Comtrade live"
    current_user = await _get_user(request, db)
    return templates.TemplateResponse("market_export.html", {"request": request, "exports": exports, "data": exports, "has_data": len(exports) > 0, "q": q, "country": country, "county": county, "source": source, "error": error, "live": live, "current_user": current_user, "user": current_user})

@router.get("/api/prices")
async def get_prices(product: str = None, county: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).order_by(desc(MarketMetric.created_at))
    if product:
        q = q.where(MarketMetric.product.ilike(f"%{product}%"))
    if county:
        q = q.where(MarketMetric.county.ilike(f"%{county}%"))
    data = db.exec(q.limit(500)).all()
    out = []
    for d in data:
        item = d.model_dump(mode='json')
        out.append(item)
    return {"total": len(out), "data": out}

@router.get("/api/demand")
async def get_demand(sector: str = None, db: Session = Depends(get_session)):
    q = select(MarketMetric).where(MarketMetric.demand_score.isnot(None)).order_by(desc(MarketMetric.demand_score))
    if sector:
        q = q.where(MarketMetric.sector.ilike(f"%{sector}%"))
    data = db.exec(q.limit(100)).all()
    return {"data": [{"product": d.product, "county": d.county, "sector": d.sector, "score": d.demand_score, "price": float(d.avg_price_kes) if d.avg_price_kes is not None else None} for d in data]}

@router.get("/api/risk")
async def get_risk(db: Session = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=14)
    news = db.exec(select(NewsArticle).where(NewsArticle.published_at >= since).order_by(desc(NewsArticle.published_at)).limit(50)).all()
    return {"risk_alerts": [n.model_dump(mode='json') for n in news], "total": len(news)}

@router.get("/api/export")
async def get_export(q: str = None, country: str = None, county: str = None, db: Session = Depends(get_session)):
    if not q:
        return {"total": 0, "data": [], "results": [], "source": "Pass ?q=tea to query UN Comtrade live", "live": True, "error": None}
    exports, source, error, live = _build_export_rows(q.strip(), (country or "").strip())
    return {"ok": True, "total": len(exports), "count": len(exports), "data": exports, "results": exports, "source": source or "", "live": live, "error": error}

# ===== Buyer Finder - Volza + LinkedIn + Alibaba + KEPROBA + Fairs =====
class KeprobaIn(BaseModel):
    company: str = ""
    product: str = ""
    hs: str = ""
    country: str = ""
    volume: str = ""
    message: str = ""
    user_email: str = ""

class SaveFairIn(BaseModel):
    fair_name: str = ""
    city: str = ""

@router.get("/api/buyers")
async def get_buyers(request: Request, q: str = None, hs: str = None, country: str = None, db: Session = Depends(get_session)):
    product = (q or "").strip()
    if not product:
        return {"ok": False, "error": "Pass ?q=coffee&country=Germany", "buyers": []}
    hs_code = (hs or _resolve_hs(product) or "").strip()
    country_clean = (country or "").strip()
    user = await _get_user(request, db)
    user_id = getattr(user, "id", None) if user else None
    if user_id:
        try:
            cached = db.exec(select(BuyerSearchCache).where(BuyerSearchCache.user_id == user_id, BuyerSearchCache.product == product.lower(), BuyerSearchCache.country == country_clean).order_by(desc(BuyerSearchCache.created_at)).limit(1)).first()
            if cached and cached.created_at and (datetime.now(UTC) - cached.created_at).days < 7 and cached.result_json:
                return {"ok": True, "cached": True, **json.loads(cached.result_json)}
        except Exception:
            pass
    result = await find_buyers(product, hs_code, country_clean)
    if result.get("volza", {}).get("available") and user_id:
        try:
            for b in result["volza"].get("buyers", []):
                if not b.get("company"):
                    continue
                exists = db.exec(select(Buyer).where(Buyer.user_id == user_id, Buyer.company == b["company"], Buyer.hs == hs_code).limit(1)).first()
                if not exists:
                    db.add(Buyer(user_id=user_id, company=b["company"], country=b.get("country") or country_clean, product=product, hs=hs_code, source="Volza", shipments=b.get("shipments"), last_shipment=str(b.get("last_shipment") or ""), contact_locked=True, contact_name=b.get("contact"), contact_email=None))
            db.add(BuyerSearchCache(user_id=user_id, product=product.lower(), hs=hs_code, country=country_clean, result_json=json.dumps(result)))
            db.commit()
        except Exception as e:
            logger.exception(f"buyer cache save failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
    return {"ok": True, "cached": False, **result}

@router.post("/api/buyers/keproba-request")
async def keproba_request(request: Request, body: KeprobaIn, db: Session = Depends(get_session)):
    user = await _get_user(request, db)
    user_id = getattr(user, "id", None) if user else None
    user_email = body.user_email or (getattr(user, "email", "") if user else "")
    if not body.product or not user_email:
        return {"ok": False, "error": "Product + email required"}
    row = KeprobaRequest(user_id=user_id, user_email=user_email, company=body.company, product=body.product, hs=body.hs, country=body.country, volume=body.volume, message=body.message, status="pending")
    db.add(row); db.commit(); db.refresh(row)
    return {"ok": True, "id": row.id, "message": "Saved. Forward this to KEPROBA / Make It Kenya with your company profile."}

@router.get("/api/buyers/keproba-requests")
async def list_keproba_requests(request: Request, db: Session = Depends(get_session)):
    user = await _get_user(request, db)
    user_id = getattr(user, "id", None) if user else None
    if not user_id:
        return {"ok": False, "error": "Login required", "requests": []}
    rows = db.exec(select(KeprobaRequest).where(KeprobaRequest.user_id == user_id).order_by(desc(KeprobaRequest.created_at)).limit(50)).all()
    return {"ok": True, "requests": [{"id": r.id, "product": r.product, "country": r.country, "status": r.status, "created_at": str(r.created_at)} for r in rows]}

@router.post("/api/buyers/save-fair")
async def save_fair(request: Request, body: SaveFairIn, db: Session = Depends(get_session)):
    user = await _get_user(request, db)
    user_id = getattr(user, "id", None) if user else None
    if not user_id or not body.fair_name:
        return {"ok": False, "error": "Login + fair_name required"}
    row = SavedFair(user_id=user_id, user_email=getattr(user, "email", "") or "", fair_name=body.fair_name, city=body.city, remind=True)
    db.add(row); db.commit()
    return {"ok": True, "message": f"Saved {body.fair_name} - you will get a reminder."}

@router.get("/api/buyers/saved")
async def list_saved_buyers(request: Request, db: Session = Depends(get_session)):
    user = await _get_user(request, db)
    user_id = getattr(user, "id", None) if user else None
    if not user_id:
        return {"ok": False, "error": "Login required", "buyers": []}
    rows = db.exec(select(Buyer).where(Buyer.user_id == user_id).order_by(desc(Buyer.created_at)).limit(100)).all()
    return {"ok": True, "buyers": [{"company": r.company, "country": r.country, "product": r.product, "hs": r.hs, "source": r.source, "shipments": r.shipments, "contact_locked": r.contact_locked} for r in rows]}
