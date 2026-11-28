# app/modules/market_engine/buyer_finder.py - PRODUCTION - Buyer finding, LIVE ONLY
# Volza = only paid API used. LinkedIn/Alibaba = deep-links, NOT scraping. No fake contacts.
import os, urllib.parse
import httpx

VOLZA_KEY = os.getenv("VOLZA_API_KEY", "")
VOLZA_URL = "https://api.volza.com/api/v1/shipments"

# Curated fairs - public event names/dates only, no trade values invented
TRADE_FAIRS = [
    {"name": "Fruit Logistica", "city": "Berlin, Germany", "month": "Feb", "url": "https://www.fruitlogistica.com", "products": ["avocado", "mango", "flowers", "french beans", "pineapple"]},
    {"name": "Gulfood", "city": "Dubai, UAE", "month": "Feb", "url": "https://www.gulfood.com", "products": ["tea", "coffee", "honey", "spices", "juice"]},
    {"name": "BioFach", "city": "Nuremberg, Germany", "month": "Feb", "url": "https://www.biofach.de", "products": ["tea", "coffee", "honey", "macadamia"]},
    {"name": "SIAL Paris", "city": "Paris, France", "month": "Oct", "url": "https://www.sialparis.com", "products": ["tea", "coffee", "avocado", "mango", "juice"]},
    {"name": "Anuga", "city": "Cologne, Germany", "month": "Oct", "url": "https://www.anuga.com", "products": ["tea", "coffee", "honey", "juice", "snacks"]},
    {"name": "IFTF - International Floriculture Trade Fair", "city": "Vijfhuizen, Netherlands", "month": "Nov", "url": "https://www.iftf.nl", "products": ["flowers", "roses"]},
    {"name": "Macfrut", "city": "Rimini, Italy", "month": "May", "url": "https://www.macfrut.com", "products": ["avocado", "mango", "pineapple", "tomato"]},
]

def linkedin_search_link(product: str, country: str):
    # Safe: pre-filled LinkedIn people search, user logs in themselves. No scraping.
    q = f"Import Manager {product} {country}"
    return f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(q)}"

def alibaba_links(product: str, country: str):
    q = urllib.parse.quote(product)
    return [
        {"label": "Browse RFQs on Alibaba", "url": f"https://www.alibaba.com/trade/search?searchText={q}"},
        {"label": "Browse Buyers on TradeKey", "url": f"https://www.tradekey.com/buyer/{q}.html"},
        {"label": "Browse on Global Sources", "url": f"https://www.globalsources.com/suppliers/{q}.html"},
    ]

def keproba_action(product: str, country: str):
    return {
        "label": "Request introduction via KEPROBA / Make It Kenya",
        "url": "https://makeitkenya.com",
        "action": "POST /market/api/buyers/keproba-request - saves your request, you forward to KEPROBA",
    }

def matching_fairs(product: str):
    p = product.lower()
    out = [f for f in TRADE_FAIRS if any(k in p or p in k for k in f["products"])]
    return out if out else TRADE_FAIRS[:3]

async def volza_search(hs: str, country: str, product: str, limit: int = 20):
    """Returns real Volza buyers if VOLZA_API_KEY set, else empty + locked flag. Never invents."""
    if not VOLZA_KEY:
        return {"available": False, "buyers": [], "reason": "VOLZA_API_KEY not set - Premium locked. Use LinkedIn / Alibaba links below."}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(VOLZA_URL, params={"hsCode": hs, "destinationCountry": country, "limit": limit}, headers={"Authorization": f"Bearer {VOLZA_KEY}"})
            if r.status_code != 200:
                return {"available": False, "buyers": [], "reason": f"Volza {r.status_code}: {r.text[:200]}"}
            buyers = []
            for row in (r.json().get("data") or r.json().get("shipments") or [])[:limit]:
                # Only map fields Volza actually returns - never invent email/phone
                buyers.append({
                    "company": row.get("consignee") or row.get("buyer") or row.get("company"),
                    "country": row.get("destinationCountry") or country,
                    "hs": row.get("hsCode") or hs,
                    "shipments": row.get("shipmentCount"),
                    "last_shipment": row.get("lastShipmentDate"),
                    "contact": row.get("contact"),  # only if Volza license includes it
                    "source": "Volza",
                })
            return {"available": True, "buyers": [b for b in buyers if b["company"]], "reason": None}
    except Exception as e:
        return {"available": False, "buyers": [], "reason": str(e)}

async def find_buyers(product: str, hs: str, country: str):
    volza = await volza_search(hs, country, product)
    return {
        "product": product, "hs": hs, "country": country,
        "volza": volza,
        "linkedin": {"label": "Search decision-makers on LinkedIn", "url": linkedin_search_link(product, country)},
        "marketplaces": alibaba_links(product, country),
        "keproba": keproba_action(product, country),
        "fairs": matching_fairs(product),
        "outreach_template": f"Subject: Kenya {product} - Direct exporter, HS {hs}\n\nHello, we export {product} from Kenya (HS {hs}) to {country}. We supply [grade / volume / season]. Can I send our spec sheet + FOB price?\n\nRegards, [Your Name] | [Company] | [WhatsApp]",
    }
