import re, logging
from datetime import datetime, timezone
import httpx
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from app.core.models import Funder, ExportOpportunity
logger = logging.getLogger("evidlens.scraper_funding")
HEADERS = {"User-Agent": "EvidLens/1.0"}
UTC = timezone.utc
def _clean(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:2000]
def _amount(text: str):
    m = re.search(r"(KES|KSh)\s?[\d,]+(?:\s?-\s?(?:KES|KSh)?\s?[\d,]+)?", text)
    return m.group(0) if m else None
def _rate(text: str):
    m = re.search(r"\d+(?:\.\d+)?\s?%\s?(?:p\.a\.|per annum)?", text)
    return m.group(0) if m else None
def _to_float(s):
    try:
        if not s: return None
        v = float(re.sub(r"[^0-9.]", "", str(s).split("-")[0]))
        return v if v > 0 else None
    except Exception:
        return None
FUNDING_SOURCES = [
    {"name": "KCB Bank - Biashara Loan", "type": "Bank", "url": "https://ke.kcbgroup.com/for-business/borrow", "sector": "All Sectors"},
    {"name": "Equity Bank - SME Loan", "type": "Bank", "url": "https://equitygroupholdings.com/ke/borrow/", "sector": "All Sectors"},
    {"name": "Co-operative Bank - MSME Loan", "type": "Bank", "url": "https://www.co-opbank.co.ke/business-banking/", "sector": "Agriculture, Retail"},
    {"name": "Uwezo Fund", "type": "Grant / Government", "url": "https://www.uwezofund.go.ke/", "sector": "Women, Youth, PWD Groups"},
    {"name": "Hustler Fund - Business", "type": "Government Loan", "url": "https://www.hustlerfund.go.ke/", "sector": "Micro Businesses"},
    {"name": "Youth Enterprise Development Fund", "type": "Grant / Government", "url": "https://www.youthfund.go.ke/", "sector": "Youth-led Businesses"},
]
EXPORT_SOURCES = [
    {"product": "Tea", "destination": "United Kingdom", "county": "Nyeri, Kericho", "url": "https://www.teaboard.or.ke/", "source_name": "Tea Board of Kenya"},
    {"product": "Coffee", "destination": "Germany", "county": "Nyeri, Kirinyaga", "url": "https://www.coffee.go.ke/", "source_name": "Coffee Directorate"},
    {"product": "Avocado", "destination": "United Arab Emirates", "county": "Muranga, Nyeri", "url": "https://www.kephis.org/", "source_name": "KEPHIS"},
    {"product": "Macadamia", "destination": "China", "county": "Embu, Nyeri", "url": "https://www.afa.go.ke/", "source_name": "Agriculture and Food Authority"},
]
def scrape_funding(db: Session):
    saved = 0
    with httpx.Client(timeout=20, follow_redirects=True, headers=HEADERS) as c:
        for s in FUNDING_SOURCES:
            try:
                r = c.get(s["url"])
                if r.status_code != 200: continue
                text = _clean(r.text)
                row = db.exec(select(Funder).where(Funder.apply_link == s["url"])).first()
                if not row:
                    row = Funder(apply_link=s["url"]); db.add(row)
                row.name = s["name"]; row.type = s["type"]; row.sector = s["sector"]; row.county = "All Counties"
                amt = _amount(text)
                if amt and "-" in amt:
                    parts = amt.replace("KES", "").replace("KSh", "").split("-")
                    row.min_amount = int(_to_float(parts[0]) or 0) or None
                    row.max_amount = int(_to_float(parts[1]) or 0) or None if len(parts) > 1 else None
                else:
                    row.min_amount = None; row.max_amount = None
                row.interest_rate = _to_float(_rate(text)); row.rating = None; row.requirements = text[:500] if text else ""; row.source_url = s["url"]; row.last_verified_at = datetime.now(UTC); saved += 1
            except Exception as e:
                logger.exception(f"funding {s['url']}: {e}")
    db.commit(); return saved
def scrape_exports(db: Session):
    saved = 0
    with httpx.Client(timeout=20, follow_redirects=True, headers=HEADERS) as c:
        for s in EXPORT_SOURCES:
            try:
                r = c.get(s["url"])
                if r.status_code != 200: continue
                text = _clean(r.text)
                row = db.exec(select(ExportOpportunity).where(ExportOpportunity.source_url == s["url"])).first()
                if not row:
                    row = ExportOpportunity(source_url=s["url"]); db.add(row)
                row.product = s["product"]; row.country = s["destination"]; row.destination = s["destination"]; row.county = s["county"]; row.description = text[:500] if text else ""; row.opportunity_score = None; row.source_name = s["source_name"]; row.last_verified_at = datetime.now(UTC); saved += 1
            except Exception as e:
                logger.exception(f"export {s['url']}: {e}")
    db.commit(); return saved
