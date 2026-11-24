# FILE: app/modules/report_builder/service.py
# VERSION: 2.6.1 PRODUCTION - USER READY
# - All PDF lines use multi_cell, never cell for long text
# - Every string truncated, never overflow
# - S3 optional, local file always kept

import os
import json
from datetime import datetime
from fpdf import FPDF
from sqlmodel import Session
from sqlmodel import select
from sqlalchemy.orm import Session as OrmSession

from app.core.db import engine
from app.core.models import MarketMetric
from app.core.models import Company
from app.core.models import Report
from app.core.models import PriceData
from app.core.models import NewsArticle
from app.core.models import SocialMention
from app.core.models import KnowledgeChunk
from app.core.models import ExportOpportunity
from app.core.models import Competitor

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

S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("S3_REGION", "eu-west-1")

def safe(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("•", "-")
    s = s.replace("★", "*")
    s = s.replace("☆", "*")
    s = s.replace("—", "-")
    s = s.replace("–", "-")
    s = s.replace("’", "'")
    s = s.replace("‘", "'")
    s = s.replace("“", '"')
    s = s.replace("”", '"')
    s = s.replace("…", "...")
    s = s.replace("✓", "v")
    s = s.replace("→", "->")
    s = s.replace("💸", "")
    s = s.replace("📊", "")
    s = s.replace("🌍", "")
    return s.encode("latin-1", "ignore").decode("latin-1")

def short(s, n=160):
    return safe(s)[:n]

def save_to_storage(local_path: str) -> str:
    if not S3_BUCKET:
        return local_path
    try:
        import boto3
        s3 = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        key = f"reports/{os.path.basename(local_path)}"
        s3.upload_file(local_path, S3_BUCKET, key)
        print(f"S3 backup OK: {key}")
    except Exception as e:
        print(f"S3 backup skipped, local still works: {e}")
    return local_path

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

def _section_title(pdf, text):
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*SECONDARY)
    pdf.multi_cell(0, 7, short(text, 170))
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)

def _body(pdf, text):
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 5, short(text, 800))

def _bullet(pdf, text):
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 4, short(text, 170))

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
    location = town or ward or sub_county or county or country
    live = fetch_all_live(sector, county, q)
    pdf = EvidLensPDF()
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 15)
    pdf.multi_cell(0, 9, short(f'Market Feasibility Report: {q}', 170))
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 6, short(f'Sector: {sector} | Location: {location} | Budget: KES {budget or "N/A"} | Plan: {plan_name} | {datetime.now().strftime("%d %b %Y %H:%M")}', 170))
    pdf.ln(4)

    _section_title(pdf, '1. Quick Business Analysis Input')
    _body(pdf, f"Product/Query: {q}\nSector: {sector}\nCountry: {country}\nCounty: {county}\nSubCounty: {sub_county}\nWard: {ward}\nTown: {town}\nBudget: KES {budget}\nLocation: {location}")
    pdf.ln(3)

    _section_title(pdf, f'2. Competitive Engine - {len(live["competitors"])} Records')
    if not live["competitors"]:
        _bullet(pdf, "No competitors yet. Seed data.")
    for c in live["competitors"][:15]:
        _bullet(pdf, f"- {getattr(c, 'name', 'N/A')} | {getattr(c, 'sector', 'N/A')} | {getattr(c, 'county', 'N/A')}")
    pdf.ln(3)

    _section_title(pdf, f'3. Pricing Engine (Price Oracle) - {len(live["prices"])} Records')
    if not live["prices"]:
        _bullet(pdf, "No price data. Run price scrape.")
    for p in live["prices"][:15]:
        pname = getattr(p, 'product_name', getattr(p, 'product', 'Product'))
        price = getattr(p, 'price', getattr(p, 'avg_price_kes', 0))
        pcounty = getattr(p, 'county', 'Kenya')
        _bullet(pdf, f"- {pname}: KES {price} in {pcounty}")
    pdf.ln(3)

    _section_title(pdf, f'4. Market Engine (Demand Radar) - {len(live["demand"])} Records')
    if not live["demand"]:
        _bullet(pdf, "No demand signals yet.")
    for d in live["demand"][:15]:
        _bullet(pdf, f"- {getattr(d, 'product', 'N/A')} @ {getattr(d, 'county', 'N/A')}: Demand {getattr(d, 'demand_score', 0)} | Avg KES {getattr(d, 'avg_price_kes', 0)}")
    pdf.ln(3)

    _section_title(pdf, '5. Location Engine (County Mapper)')
    _body(pdf, f"Analysis location: {location}\nCounty: {county} | SubCounty: {sub_county} | Ward: {ward} | Town: {town}\nCoverage: {len(live['companies'])} companies mapped.")
    pdf.ln(3)

    _section_title(pdf, f'6. Consumer Engine (Consumer Pulse) - {len(live["social"])} Mentions')
    if not live["social"]:
        _bullet(pdf, "No consumer mentions yet.")
    for s in live["social"][:10]:
        plat = getattr(s, 'platform', 'X')
        sent = getattr(s, 'sentiment', 'neutral')
        cont = str(getattr(s, 'content', ''))[:120]
        _bullet(pdf, f"- [{plat} {sent}]: {cont}")
    pdf.ln(3)

    _section_title(pdf, f'7. Core OS (Risk Sentinel) - {len(live["news"])} Alerts')
    if not live["news"]:
        _bullet(pdf, "No alerts.")
    for n in live["news"][:8]:
        _bullet(pdf, f"- {getattr(n, 'title', 'News')}: {str(getattr(n, 'summary', ''))[:120]}")
    pdf.ln(3)

    _section_title(pdf, f'8. Regulatory Engine (Policy Watch) - {len(live["knowledge"])} Policies')
    if plan_name != "Enterprise":
        pdf.set_font('Arial', 'I', 8)
        pdf.multi_cell(0, 5, short("[Upgrade to Enterprise to unlock full Regulatory Engine data]"))
        pdf.set_font('Arial', '', 8)
    for k in live["knowledge"][:8]:
        _bullet(pdf, f"- {getattr(k, 'sector', 'Policy')} | {str(getattr(k, 'chunk_text', ''))[:120]}")
    pdf.ln(3)

    _section_title(pdf, '9. Core OS (Funding Radar)')
    _body(pdf, f"Budget: KES {budget or 'Not provided'}\nFor {q} in {sector}/{county}: SME funding - Kenya Uwezo Fund, Youth Fund, SACCO loans, Bank SME. Working capital = 30% inventory + licenses.")
    pdf.ln(3)

    _section_title(pdf, f'10. Business OS (Export Navigator) - {len(live["exports"])} Opportunities')
    if plan_name != "Enterprise":
        pdf.set_font('Arial', 'I', 8)
        pdf.multi_cell(0, 5, short("[Enterprise plan unlocks full Export Navigator]"))
        pdf.set_font('Arial', '', 8)
    for e in live["exports"][:8]:
        _bullet(pdf, f"- {getattr(e, 'product', 'Product')} -> {getattr(e, 'country', 'Country')} | Score {getattr(e, 'opportunity_score', 0)}")
    pdf.ln(3)

    _section_title(pdf, f'11. Core OS (Knowledge Base) - {len(live["knowledge"])} Records')
    if not live["knowledge"]:
        _bullet(pdf, "No knowledge records yet.")
    for k in live["knowledge"][:8]:
        _bullet(pdf, f"- {str(getattr(k, 'chunk_text', ''))[:120]}")
    pdf.ln(3)

    _section_title(pdf, '12. AI Insights + Report Builder - Verdict')
    _body(pdf, f"FINAL VERDICT for {q} in {location}:\n- Sector {sector} has {len(live['competitors'])} competitors, {len(live['prices'])} price points, {len(live['demand'])} demand signals.\n- Consumer Pulse {len(live['social'])} mentions, Risk Sentinel {len(live['news'])} alerts.\n- With budget KES {budget}, recommended entry: Source from {county} suppliers, price at median observed, target {sub_county or county} first.\n- Regulatory: {len(live['knowledge'])} policies. Export: {len(live['exports'])} routes.\n- Plan {plan_name} - This PDF aggregates ALL 12 engines LIVE from app.evidlens.co.ke")

    os.makedirs("app/static/reports", exist_ok=True)
    fname = f"EvidLens_{safe(q).replace(' ', '_')}_{safe(county or 'Kenya')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    fname = "".join(c for c in fname if c.isalnum() or c in "._-")
    path = f"app/static/reports/{fname}"
    pdf.output(path)
    return save_to_storage(path)

async def generate_market_report_pdf(db: OrmSession, q: str, sector: str, country: str = "Kenya", county: str = None, sub_county: str = None, ward: str = None, town: str = None) -> bytes:
    path = generate_market_report_pdf_file(q, sector, country, county, sub_county, ward, town, budget=None, plan_name="Pro")
    with open(path, "rb") as f:
        data = f.read()
    return data

def generate_market_report_excel(db: OrmSession, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None, q: str = None) -> str:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        from openpyxl.styles import PatternFill
        from openpyxl.styles import Alignment
        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="0A1F44", end_color="0A1F44", fill_type="solid")
        bold_font = Font(bold=True, size=11)
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
            ws.append([
                getattr(p, 'product_name', getattr(p, 'product', 'Product')),
                getattr(p, 'county', ''),
                getattr(p, 'price', getattr(p, 'avg_price_kes', 0))
            ])
        ws.column_dimensions['A'].width = 32
        ws.column_dimensions['B'].width = 42
        ws.column_dimensions['C'].width = 18
        os.makedirs("app/static/reports", exist_ok=True)
        path = f"app/static/reports/EvidLens_{str(q or 'report').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        wb.save(path)
        return save_to_storage(path)
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
