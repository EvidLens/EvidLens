import os
import json
from datetime import datetime
from fpdf import FPDF
from sqlalchemy.orm import Session
# from app.modules.market_intel.service import search_market
from app.modules.ai_insights.service import AIInsightsService
from app.modules.knowledge_base.service import get_sector_benchmark

ai_service = AIInsightsService()

PRIMARY = (10, 31, 68)
SECONDARY = (20, 184, 166)
ACCENT = (245, 158, 11)

class EvidLensPDF(FPDF):
    def header(self):
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 30, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'EvidLens', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Kenya Decision Intelligence Platform', 0, 1, 'L')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_text_color(100, 100, 100)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'EvidLens Kenya Sector Data | Page {self.page_no()}', 0, 0, 'C')

async def generate_market_report_pdf(
    db: Session,
    q: str,
    sector: str,
    country: str = "Kenya",
    county: str = None,
    sub_county: str = None,
    ward: str = None,
    town: str = None
) -> bytes:
    try:
        # market_data = search_market(db, q, sector, country, county, sub_county, ward, town)
        market_data = {"demand_level": "N/A", "market_size_kes": 0, "price_range": {"avg": 0}, "competitor_count": 0, "growth_rate": 0}

        location_str = town or ward or sub_county or county or country
        market_dict = {"sector": sector, "county": county, "sub_county": sub_county, "ward": ward}

        ai_json = await ai_service.generate_insights(q, market_dict)
        benchmark = get_sector_benchmark(sector)

    except Exception as e:
        ai_json = {"answer": str(e), "verdict": "N/A", "chart": None, "table": [], "map": None, "sources": []}
        benchmark = {}

    pdf = EvidLensPDF()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)

    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'Market Feasibility Report: {q}', 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, f'Sector: {sector} | Location: {location_str} | Generated: {datetime.now().strftime("%d %b %Y")}', 0, 1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 8, '1. Executive Summary - Lens AI', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f"Verdict: {ai_json.get('verdict')}\n\n{ai_json.get('answer')}")
    pdf.ln(3)

    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 8, '2. Market Metrics', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 6, f"Demand Level: {market_data.get('demand_level', 'N/A')}", 0, 0)
    pdf.cell(95, 6, f"Market Size: KES {market_data.get('market_size_kes', 0):,.0f}", 0, 1)
    pdf.cell(95, 6, f"Growth Rate: {market_data.get('growth_rate', 0)}%", 0, 0)
    pdf.cell(95, 6, f"Avg Price: KES {market_data.get('price_range', {}).get('avg', 0):,.0f}", 0, 1)
    pdf.cell(95, 6, f"Competitors: {market_data.get('competitor_count', 0)}", 0, 1)

    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'FOR BUSINESS PLANNING PURPOSES', 0, 1, 'C', 1)

    return pdf.output(dest='S').encode('latin1')

def generate_market_report_excel(db: Session, sector: str, country: str, county: str = None, sub_county: str = None, ward: str = None, town: str = None, q: str = None) -> bytes:
    return b""

generate_report_pdf = generate_market_report_pdf
