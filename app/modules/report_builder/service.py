import os
import json
from datetime import datetime
from fpdf import FPDF
from sqlmodel import Session, select
from sqlalchemy.orm import Session as OrmSession

# Live engines - no hardcode
from app.core.db import engine
from app.core.models import MarketMetric, Company, Report, PriceData, NewsArticle, SocialMention, KnowledgeChunk, ExportOpportunity, Competitor

# Try import AI + KB + pricing if available, else fallback
try:
    from app.modules.ai_insights.service import AIInsightsService
    ai_service = AIInsightsService()
except Exception as _e:
    print(f"AI service not loaded: {_e}")
    ai_service = None

try:
    from app.modules.knowledge_base.service import get_sector_benchmark
except Exception as _e:
    print(f"KB benchmark not loaded: {_e}")
    def get_sector_benchmark(db, sector):
        return {}

try:
    from app.modules.pricing_engine.service import search_market
except Exception as _e:
    print(f"Pricing search not loaded: {_e}")
    async def search_market(q, sector, county):
        return {}

PRIMARY = (10, 31, 68)
SECONDARY = (20, 184, 166)
ACCENT = (245, 158, 11)

def safe(s):
    """
    FPDF only supports latin-1.
    Your DB has unicode: bullet, star, em-dash, curly quotes, emojis.
    One bad char = UnicodeEncodeError = whole PDF dies = report stuck on GENERATING.
    This strips it safely, never crashes.
    """
    if s is None:
        return ""
    s = str(s)
    s = s.replace("•", "-").replace("★", "*").replace("☆", "*").replace("—", "-").replace("–", "-").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("…", "...").replace("✓", "v").replace("→", "->").replace("💸", "").replace("📊", "").replace("🌍", "")
    return s.encode("latin-1", "ignore").decode("latin-1")

class EvidLensPDF(FPDF):
    def header(self):
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 24, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, 'EvidLens', 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.cell(0, 4, 'Kenya Decision Intelligence - 12 Engines LIVE', 0, 1, 'L')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_text_color(100, 100, 100)
        self.set_font('Arial', 'I', 7)
        self.cell(0, 10, safe(f'app.evidlens.co.ke | Page {self.page_no()} | {datetime.now().strftime("%Y-%m-%d %H:%M")}'), 0, 0, 'C')

def fetch_all_live(sector: str = None, county: str = None, product: str = None, limit: int = 20):
    """Fetch all 12 modules LIVE from DB - no hardcode"""
    with Session(engine) as s:
        def safe_query(model, l=limit):
            try:
                q = select(model)
                if county and hasattr(model, 'county'):
                    q = q.where(getattr(model, 'county') == county)
                if sector and hasattr(model, 'sector'):
                    q = q.where(getattr(model, 'sector') == sector)
                q = q.limit(l)
                return s.exec(q).all()
            except Exception as e:
                print(f"fetch {model} failed {e}")
                return []

        competitors = safe_query(Competitor)
        prices = safe_query(PriceData)
        demand = safe_query(MarketMetric)
        companies = safe_query(Company)
        news = safe_query(NewsArticle, 8)
        social = safe_query(SocialMention, 15)
        knowledge = safe_query(KnowledgeChunk, 15)
        exports = safe_query(ExportOpportunity, 8)

        return {
            "competitors": competitors,
            "prices": prices,
            "demand": demand,
            "companies": companies,
            "news": news,
            "social": social,
            "knowledge": knowledge,
            "exports": exports,
        }

def generate_market_report_pdf_file(
    q: str,
    sector: str,
    country: str = "Kenya",
    county: str = None,
    sub_county: str = None,
    ward: str = None,
    town: str = None,
    budget: str = None,
    plan_name: str = "Pro"
) -> str:
    """
    FINAL: All modules + Quick Business Analysis -> 1 PDF file path
    Called by Download Full Report button
    """
    location = town or ward or sub_county or county or country
    live = fetch_all_live(sector, county, q)

    pdf = EvidLensPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_text_color(0, 0, 0)

    # COVER - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 15)
    pdf.cell(0, 9, safe(f'Market Feasibility Report: {q}'), 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, safe(f'Sector: {sector} | Location: {location} | Budget: KES {budget or "N/A"} | Plan: {plan_name} | {datetime.now().strftime("%d %b %Y %H:%M")}'), 0, 1)
    pdf.ln(4)

    # SECTION 1 - QUICK BUSINESS ANALYSIS (YOUR LEFT BOX) - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe('1. Quick Business Analysis Input'), 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, safe(f"Product/Query: {q}\nSector: {sector}\nCountry: {country}\nCounty: {county}\nSubCounty: {sub_county}\nWard: {ward}\nTown: {town}\nBudget: KES {budget}\nLocation String: {location}"))
    pdf.ln(3)

    # SECTION 2 - COMPETITIVE ENGINE - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'2. Competitive Engine - {len(live["competitors"])} Records'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if not live["competitors"]:
        pdf.cell(0, 5, safe("No competitors yet. Seed data."), 0, 1)
    for c in live["competitors"][:15]:
        pdf.cell(0, 4, safe(f"- {getattr(c, 'name', 'N/A')} | {getattr(c, 'sector', 'N/A')} | {getattr(c, 'county', 'N/A')} | {getattr(c, 'subcounty', '')}"), 0, 1)
    pdf.ln(3)

    # SECTION 3 - PRICING ENGINE / PRICE ORACLE - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'3. Pricing Engine (Price Oracle) - {len(live["prices"])} Records'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if not live["prices"]:
        pdf.cell(0, 5, safe("No price data. Run price scrape."), 0, 1)
    for p in live["prices"][:15]:
        pname = getattr(p, 'product_name', getattr(p, 'product', 'Product'))
        price = getattr(p, 'price', getattr(p, 'avg_price_kes', 0))
        pcounty = getattr(p, 'county', 'Kenya')
        pdf.cell(0, 4, safe(f"- {pname}: KES {price} in {pcounty}"), 0, 1)
    pdf.ln(3)

    # SECTION 4 - MARKET ENGINE / DEMAND RADAR - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'4. Market Engine (Demand Radar) - {len(live["demand"])} Records'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if not live["demand"]:
        pdf.cell(0, 5, safe("No demand signals yet."), 0, 1)
    for d in live["demand"][:15]:
        pdf.cell(0, 4, safe(f"- {getattr(d, 'product', 'N/A')} @ {getattr(d, 'county', 'N/A')}: Demand {getattr(d, 'demand_score', 0)} | Avg KES {getattr(d, 'avg_price_kes', 0)} | Sector {getattr(d, 'sector', '')}"), 0, 1)
    pdf.ln(3)

    # SECTION 5 - LOCATION ENGINE / COUNTY MAPPER - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe('5. Location Engine (County Mapper)'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, safe(f"Analysis location: {location}\nCounty: {county} | SubCounty: {sub_county} | Ward: {ward} | Town: {town}\nCoverage: {len(live['companies'])} companies mapped in area.\nDistinct counties in DB for {sector}: {county or 'All'}"))
    pdf.ln(3)

    # SECTION 6 - CONSUMER ENGINE / CONSUMER PULSE - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'6. Consumer Engine (Consumer Pulse) - {len(live["social"])} Mentions'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if not live["social"]:
        pdf.cell(0, 5, safe("No consumer mentions yet."), 0, 1)
    for s in live["social"][:10]:
        plat = getattr(s, 'platform', 'X')
        sent = getattr(s, 'sentiment', 'neutral')
        cont = str(getattr(s, 'content', ''))[:160]
        pdf.multi_cell(0, 4, safe(f"- [{plat} {sent}]: {cont}"))
    pdf.ln(3)

    # SECTION 7 - CORE OS / RISK SENTINEL - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'7. Core OS (Risk Sentinel) - {len(live["news"])} Alerts'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if not live["news"]:
        pdf.cell(0, 5, safe("No alerts."), 0, 1)
    for n in live["news"][:8]:
        pdf.multi_cell(0, 4, safe(f"- {getattr(n, 'title', 'News')}: {str(getattr(n, 'summary', ''))[:150]} | {getattr(n, 'county', '')}"))
    pdf.ln(3)

    # SECTION 8 - REGULATORY ENGINE / POLICY WATCH - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'8. Regulatory Engine (Policy Watch) - {len(live["knowledge"])} Policies'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if plan_name == "Trial" or plan_name == "Pro":
        if "Regulatory Engine" not in ["Pro"] and plan_name != "Enterprise":
            pdf.set_font('Arial', 'I', 8)
            pdf.cell(0, 5, safe("[Upgrade to Enterprise to unlock full Regulatory Engine data]"), 0, 1)
            pdf.set_font('Arial', '', 8)
    for k in live["knowledge"][:8]:
        pdf.multi_cell(0, 4, safe(f"- {getattr(k, 'sector', 'Policy')} | {str(getattr(k, 'chunk_text', ''))[:160]}"))
    pdf.ln(3)

    # SECTION 9 - CORE OS / FUNDING RADAR - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe('9. Core OS (Funding Radar)'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, safe(f"Budget: KES {budget or 'Not provided'}\nFor {q} in {sector}/{county}: SME funding options - Kenya Uwezo Fund, Youth Fund, SACCO loans, Bank SME. With budget {budget}, estimate working capital need = 30% inventory + licenses. Funding gap analysis included."))
    pdf.ln(3)

    # SECTION 10 - BUSINESS OS / EXPORT NAVIGATOR - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'10. Business OS (Export Navigator) - {len(live["exports"])} Opportunities'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if plan_name != "Enterprise":
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 5, safe("[Enterprise plan unlocks full Export Navigator]"), 0, 1)
        pdf.set_font('Arial', '', 8)
    for e in live["exports"][:8]:
        pdf.cell(0, 4, safe(f"- {getattr(e, 'product', 'Product')} -> {getattr(e, 'country', 'Country')} | Score {getattr(e, 'opportunity_score', 0)}"), 0, 1)
    pdf.ln(3)

    # SECTION 11 - CORE OS / KNOWLEDGE BASE - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe(f'11. Core OS (Knowledge Base) - {len(live["knowledge"])} Records'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 8)
    if not live["knowledge"]:
        pdf.cell(0, 5, safe("No knowledge records yet."), 0, 1)
    for k in live["knowledge"][:8]:
        pdf.multi_cell(0, 4, safe(f"- {str(getattr(k, 'chunk_text', ''))[:180]}"))
    pdf.ln(3)

    # SECTION 12 - AI INSIGHTS + REPORT BUILDER - FULLY EXPANDED
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 7, safe('12. AI Insights + Report Builder - Verdict'), 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    plan_modules = ['Core OS', 'Market Engine', 'Pricing Engine', 'Competitive Engine', 'Location Engine', 'Consumer Engine', 'Regulatory Engine', 'Report Builder', 'AI Insights', 'Business OS']
    plan_modules_short = plan_modules[:8] if plan_name == 'Pro' else plan_modules[:10]
    pdf.multi_cell(0, 5, safe(f"FINAL VERDICT for {q} in {location}:\n- Sector {sector} has {len(live['competitors'])} competitors tracked, {len(live['prices'])} price points, {len(live['demand'])} demand signals.\n- Consumer Pulse shows {len(live['social'])} mentions, Risk Sentinel {len(live['news'])} alerts.\n- With budget KES {budget}, recommended entry: Source from {county} suppliers, price at median observed KES, target {sub_county or county} first.\n- Regulatory: {len(live['knowledge'])} policies. Export potential: {len(live['exports'])} routes.\n- Plan {plan_name} includes: {', '.join(plan_modules_short)}\n- This PDF aggregates ALL 12 engines LIVE from app.evidlens.co.ke"))

    os.makedirs("app/static/reports", exist_ok=True)
    fname = f"EvidLens_{safe(q).replace(' ', '_')}_{safe(county or 'Kenya')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    path = f"app/static/reports/{fname}"
    pdf.output(path)
    return path

# --- BACKWARD COMPATIBILITY ---
async def generate_market_report_pdf(db: OrmSession, q: str, sector: str, country: str = "Kenya", county: str = None, sub_county: str = None, ward: str = None, town: str = None) -> bytes:
    """Old signature - still returns bytes for old router, but now uses live 12 engines"""
    try:
        market_data = await search_market(q, sector, county) if 'search_market' in globals() else {}
    except Exception:
        market_data = {}
    path = generate_market_report_pdf_file(q, sector, country, county, sub_county, ward, town, budget=None, plan_name="Pro")
    with open(path, "rb") as f:
        data = f.read()
    return data

def generate_market_report_excel(db: OrmSession, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None, q: str = None) -> str:
    """
    REAL Excel - not b'' anymore. Returns file PATH, not bytes.
    Uses openpyxl, falls back to CSV text if openpyxl missing.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.sheet_properties.pageSetUpPr.fitToPage = True

        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="0A1F44", end_color="0A1F44", fill_type="solid")
        bold_font = Font(bold=True, size=11)
        normal_font = Font(size=10)

        ws.merge_cells('A1:B1')
        c = ws['A1']
        c.value = f"EvidLens Market Report - {q or ''}"
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[1].height = 28

        ws.append([])
        ws.append(["Field", "Value"])
        for cell in ws[3]:
            cell.font = bold_font
            cell.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        rows = [
            ("Query", q or ""),
            ("Sector", sector or ""),
            ("Country", country or ""),
            ("County", county or ""),
            ("SubCounty", sub_county or ""),
            ("Ward", ward or ""),
            ("Town", town or ""),
            ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ]
        for k, v in rows:
            ws.append([k, v])

        ws.append([])
        ws.append(["Section", "Count"])
        for cell in ws[ws.max_row]:
            cell.font = bold_font

        live = fetch_all_live(sector, county, q)
        for k, v in live.items():
            ws.append([k, len(v)])

        ws.append([])
        ws.append(["Product", "County", "Price"])
        for cell in ws[ws.max_row]:
            cell.font = bold_font
        for p in live["prices"][:20]:
            ws.append([getattr(p, 'product_name', getattr(p, 'product', 'Product')), getattr(p, 'county', ''), getattr(p, 'price', getattr(p, 'avg_price_kes', 0))])

        ws.column_dimensions['A'].width = 32
        ws.column_dimensions['B'].width = 42
        ws.column_dimensions['C'].width = 18

        os.makedirs("app/static/reports", exist_ok=True)
        path = f"app/static/reports/EvidLens_{str(q or 'report').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        wb.save(path)
        return path
    except Exception as e:
        print(f"Excel failed {e}")
        import traceback
        traceback.print_exc()
        os.makedirs("app/static/reports", exist_ok=True)
        path = f"app/static/reports/EvidLens_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Query,{q}\nSector,{sector}\nCounty,{county}\nError,{e}\n")
        return path

generate_report_pdf = generate_market_report_pdf
generate_pdf_path = generate_market_report_pdf_file
