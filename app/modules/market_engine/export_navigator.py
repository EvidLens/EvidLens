# Export Navigator - LIVE ONLY. No seed. No curated values. No fake numbers.
# Source: UN Comtrade Public Preview API (no key needed for preview) + keyed API if COMTRADE_KEY set.
# If Comtrade returns nothing, API returns empty + error. It NEVER invents a value.
import os, math, time
import httpx
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

COMTRADE_KEY = os.getenv("COMTRADE_KEY", "")
# Public preview works without key, limited to 500 rows. Keyed API = full.
PUBLIC_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
KEYED_URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"

# HS catalogue is NOT data - it is just product names + HS codes (public HS classification)
# No values, no growth, no shares here. Values come ONLY from Comtrade live.
HS_CATALOGUE = {
 "090230": ("Black Tea", "Kericho,Nandi,Nyeri,Muranga"),
 "090111": ("Coffee, not roasted", "Nyeri,Kiambu,Muranga,Kirinyaga,Meru"),
 "080440": ("Avocados", "Muranga,Nyeri,Kiambu,Meru,Nakuru"),
 "060319": ("Cut Flowers, fresh", "Nakuru,Naivasha,Kiambu,Nyeri"),
 "060311": ("Roses", "Nakuru,Naivasha"),
 "080261": ("Macadamia nuts", "Embu,Nyeri,Kirinyaga,Meru"),
 "080430": ("Pineapples", "Thika,Kiambu,Muranga"),
 "080450": ("Mangoes", "Makueni,Machakos,Meru,Kilifi"),
 "070820": ("French Beans", "Kirinyaga,Muranga,Kiambu,Meru"),
 "070920": ("Asparagus", "Nakuru,Kiambu"),
 "071310": ("Peas, dried", "Nakuru,Laikipia"),
 "080131": ("Cashew nuts", "Kilifi,Kwale,Lamu"),
 "080119": ("Coconuts", "Kilifi,Kwale"),
 "040900": ("Natural Honey", "Baringo,Kitui,West Pokot"),
 "030461": ("Tilapia fillets", "Siaya,Kisumu,Homa Bay"),
 "030619": ("Fish, frozen", "Kisumu,Siaya"),
 "100590": ("Maize", "Trans Nzoia,Uasin Gishu,Nakuru"),
 "170199": ("Cane Sugar", "Kakamega,Bungoma,Kisumu"),
 "130219": ("Pyrethrum extracts", "Nakuru,Nyandarua"),
 "090500": ("Vanilla", "Bungoma"),
 "120740": ("Sesame seeds", "Busia,Bungoma"),
 "090121": ("Coffee, roasted", "Kiambu,Nyeri"),
 "210111": ("Coffee extracts", "Kiambu"),
 "200940": ("Pineapple juice", "Thika"),
 "200989": ("Fruit juices", "Thika,Nairobi"),
 "070310": ("Onions", "Taita Taveta,Kajiado"),
 "070200": ("Tomatoes", "Kirinyaga,Kajiado"),
 "080510": ("Oranges", "Makueni,Meru"),
 "080550": ("Lemons / limes", "Makueni,Meru"),
 "081090": ("Passion fruit", "Nyeri,Muranga"),
 "100630": ("Rice, semi-milled", "Mwea,Kirinyaga"),
 "520100": ("Cotton", "Siaya,Busia"),
 "610910": ("T-shirts, cotton", "Nairobi,EPZ"),
 "620342": ("Trousers, cotton", "Nairobi,EPZ"),
 "640399": ("Footwear, leather", "Nairobi"),
 "721420": ("Steel bars", "Nairobi,Mombasa"),
 "940360": ("Wooden furniture", "Nairobi"),
}
NAME_TO_HS = {v[0].lower(): k for k, v in HS_CATALOGUE.items()}

def _norm(v, lo, hi):
    if v is None: return None
    return max(0, min(100, (v - lo) / (hi - lo) * 100)) if hi != lo else 50

def score_live(value_m, growth, tariff, county_match, county):
    # Only use factors we actually have live. Missing factor = excluded, weights re-normalised.
    # No invented tariff, no invented share.
    parts = []
    size = _norm(math.log10(max(value_m, 0.01) + 1), 0, 3.5)
    parts.append((size, 0.40))  # market size - we have this live
    if growth is not None:
        parts.append((_norm(growth, -20, 30), 0.30))  # growth - computed from 2023 vs 2024 live
    if tariff is not None:
        parts.append((100 - _norm(tariff, 0, 20), 0.15))
    # Production: county match is user input + catalogue, not a trade value
    prod = 75 if county_match else (60 if not county else 45)
    parts.append((prod, 0.15))
    total_w = sum(w for _, w in parts)
    total = round(sum(s * w for s, w in parts) / total_w) if total_w else 0
    return total, "strong" if total >= 70 else "moderate" if total >= 40 else "weak"

async def fetch_comtrade_live(hs: str, year: int):
    """Returns dict partner -> value_usd. LIVE ONLY. Empty dict if Comtrade fails."""
    # Try keyed API first if key exists, else public preview
    url = KEYED_URL if COMTRADE_KEY else PUBLIC_URL
    headers = {"Ocp-Apim-Subscription-Key": COMTRADE_KEY} if COMTRADE_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, params={"reporterCode": "404", "period": str(year), "flowCode": "X", "partnerCode": "0", "cmdCode": hs}, headers=headers)
            if r.status_code != 200:
                return {}, f"Comtrade {r.status_code}: {r.text[:200]}"
            data = r.json().get("data", [])
            out = {}
            for row in data:
                partner = row.get("partnerDesc", "")
                if partner in ("World", "Kenya", ""): continue
                out[partner] = {"value_usd": float(row.get("primaryValue") or 0), "qty_kg": float(row.get("netWgt") or 0), "partner_code": row.get("partnerCode")}
            return out, None
    except Exception as e:
        return {}, str(e)

def resolve_hs(product: str):
    if not product: return None
    p = product.lower().strip()
    if p in HS_CATALOGUE: return p
    for name, hs in NAME_TO_HS.items():
        if p in name or name in p: return hs
    for name, hs in NAME_TO_HS.items():
        if any(w in name for w in p.split() if len(w) > 3): return hs
    return None

@router.get("/api/export/opportunities")
async def api_opportunities(product: str = "", destination: str = "", county: str = "", page: int = 1, limit: int = 50, sort: str = "score"):
    limit = max(1, min(limit, 200)); page = max(1, page)
    if not product:
        return {"opportunities": [], "total": 0, "page": page, "limit": limit, "has_more": False, "count": 0, "scored": 0, "destinations": 0, "hs": None, "source": "Search a product to query UN Comtrade live", "live": True, "error": None}
    hs = resolve_hs(product)
    if not hs:
        return {"opportunities": [], "total": 0, "page": page, "limit": limit, "has_more": False, "count": 0, "scored": 0, "destinations": 0, "hs": None, "source": "No HS match", "live": False, "error": f"No HS code found for '{product}'. Try: tea, coffee, avocado, flowers, macadamia", "suggestions": sorted([v[0] for v in HS_CATALOGUE.values()])}

    # LIVE: fetch 2024 + 2023 to compute real growth
    data_2024, err1 = await fetch_comtrade_live(hs, 2024)
    data_2023, err2 = await fetch_comtrade_live(hs, 2023)
    if not data_2024 and err1:
        return {"opportunities": [], "total": 0, "page": page, "limit": limit, "has_more": False, "count": 0, "scored": 0, "destinations": 0, "hs": hs, "hs_name": HS_CATALOGUE[hs][0], "source": "UN Comtrade Live", "live": False, "error": f"Comtrade failed: {err1}. Try again in 1 min or add COMTRADE_KEY in Render."}
    if not data_2024:
        return {"opportunities": [], "total": 0, "page": page, "limit": limit, "has_more": False, "count": 0, "scored": 0, "destinations": 0, "hs": hs, "hs_name": HS_CATALOGUE[hs][0], "source": "UN Comtrade Live (2024) - Kenya Reporter 404", "live": True, "error": "No Comtrade records for this HS in 2024. Kenya may not have exported this HS in 2024, or data not yet published."}

    name, counties = HS_CATALOGUE[hs]
    out = []
    for partner, d24 in data_2024.items():
        if destination and destination.lower() not in partner.lower(): continue
        v24 = d24["value_usd"]; v23 = data_2023.get(partner, {}).get("value_usd", 0)
        growth = round((v24 - v23) / v23 * 100, 1) if v23 and v23 > 0 else None  # None = unknown, NOT invented 5%
        value_m = round(v24 / 1_000_000, 2)
        qty = d24["qty_kg"]; unit_value = round(v24 / qty, 2) if qty else None
        cm = bool(county and county.lower() in counties.lower())
        sc, band = score_live(value_m, growth, None, cm, county)  # tariff=None = we don't invent tariff
        out.append({"product": name, "hs": hs, "destination": partner, "value": value_m, "value_usd": v24, "growth": growth, "kenya_share": None, "tariff": None, "distance": None, "county": counties, "score": sc, "band": band, "breakdown": {"market_size": round(_norm(math.log10(max(value_m, 0.01)+1), 0, 3.5)), "growth": _norm(growth, -20, 30) if growth is not None else None}, "reasons": [f"Live Kenya exports 2024: ${value_m}M to {partner}", f"Growth 2023→2024: {growth}% " if growth is not None else "Growth: not enough history", f"Unit value: ${unit_value}/kg" if unit_value else "Unit value: not reported"], "year": 2024, "unit_value": unit_value, "source": "UN Comtrade"})
    if sort == "score": out = sorted(out, key=lambda x: x["score"], reverse=True)
    if sort == "value": out = sorted(out, key=lambda x: x["value"], reverse=True)
    if sort == "growth": out = sorted(out, key=lambda x: (x["growth"] is None, -(x["growth"] or 0)))
    total = len(out); start = (page-1)*limit; end = start+limit
    return {"opportunities": out[start:end], "total": total, "page": page, "limit": limit, "has_more": end < total, "count": len(out[start:end]), "scored": total, "destinations": len(set(o["destination"] for o in out)), "hs": hs, "hs_name": name, "source": "UN Comtrade Live (2024 + 2023 for growth) - Kenya Reporter 404 - https://comtradeapi.un.org", "live": True, "error": None}

@router.get("/api/export/search")
def search_products(q: str = ""):
    q = q.lower().strip()
    out = [{"hs": hs, "name": v[0], "counties": v[1]} for hs, v in HS_CATALOGUE.items() if q in v[0].lower() or q in hs]
    return {"results": out[:50], "total": len(out)}

@router.get("/market/export")
def export_page(request: Request):
    return templates.TemplateResponse("export.html", {"request": request})
