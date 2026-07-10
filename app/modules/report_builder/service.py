import os
import json
from datetime import datetime
from fpdf import FPDF
from sqlalchemy.orm import Session

from app.modules.market_engine.service import search_market
from app.modules.ai_insights.service import generate_insights
from app.modules.knowledge_base.service import get_sector_benchmark

PRIMARY = (10, 31, 68) #0A1F44 Dark Navy
SECONDARY = (20, 184, 166) #14B8A6 Teal
ACCENT = (245, 158, 11) #F59E0B Mustard

class EvidLensPDF(FPDF):
    def header(self):
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 30, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'EvidLens', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Kenya’s Decision Intelligence Platform', 0, 1, 'L')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_text_color(100, 100, 100)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Powered by EvidLens Kenya Sector Data | Page {self.page_no()}', 0, 0, 'C')

def generate_report_pdf(db: Session, query: str, sector: str, county: str) -> bytes:
    """
    REAL v1 Report Builder 
    Takes DB session, runs real search_market, real generate_insights, real PDF
    """
    # 1. Get REAL market data
    market_data = search_market(db, query, sector, county)
    
    # 2. Get REAL AI insight
    market_dict = {"sector": sector, "county": county}
    ai_raw = generate_insights(query, market_dict)
    ai_json = json.loads(ai_raw.replace("### Lens AI Analysis\n```json\n", "").replace("\n```", ""))
    
    # 3. Get benchmark
    benchmark = get_sector_benchmark(sector)

    pdf = EvidLensPDF()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)

    # Title
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'Market Feasibility Report: {query}', 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, f'Sector: {sector} | County: {county} | Generated: {datetime.now().strftime("%d %b %Y")}', 0, 1)
    pdf.ln(5)

    # Section 1: Executive Summary
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 8, '1. Executive Summary - Lens AI', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f"Recommendation: {ai_json.get('recommendation')}\n\nViability: {ai_json.get('viability')}\n{ai_json.get('risk_analysis')}")
    pdf.ln(3)

    # Section 2: Market Metrics
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 8, '2. Market Metrics', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(95, 6, f"Demand Level: {market_data.get('demand_level', 'N/A')}", 0, 0)
    pdf.cell(95, 6, f"Market Size: KES {market_data.get('market_size_kes', 0):,.0f}", 0, 1)
    pdf.cell(95, 6, f"Avg Price: KES {market_data.get('price_range', {}).get('avg_kes', 0):,.0f}", 0, 0)
    pdf.cell(95, 6, f"Competitors: {market_data.get('competitor_count', 0)}", 0, 1)
    pdf.ln(3)

    # Section 3: Risk + Pricing
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, '3. Risk Analysis & Strategy', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f"Saturation: {ai_json.get('saturation')}\nPricing Strategy: {ai_json.get('pricing_strategy')}")
    pdf.ln(5)

    # KRA Footer
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'KRA COMPLIANT REPORT - FOR BUSINESS PLANNING PURPOSES', 0, 1, 'C', 1)

    return pdf.output(dest='S').encode('latin1')
