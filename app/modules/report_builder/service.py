import os
import json
from datetime import datetime
from fpdf import FPDF
from sqlalchemy.orm import Session
from app.modules.market_engine.service import search_market
from app.modules.ai_insights.service import generate_insights
from app.modules.knowledge_base.service import get_sector_benchmark

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
        self.cell(0, 6, 'Kenya’s Decision Intelligence Platform', 0, 1, 'L')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_text_color(100, 100, 100)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Powered by EvidLens Kenya Sector Data | Page {self.page_no()}', 0, 0, 'C')

def generate_market_report_pdf(db: Session, q: str, sector: str, county: str) -> bytes: # FIXED ORDER TO MATCH ROUTES
    try:
        market_data = search_market(db, q, sector, county)
        market_dict = {"sector": sector, "county": county, "q": q}
        ai_raw = generate_insights(q, market_dict)
        ai_json = json.loads(ai_raw.replace("### Lens AI Analysis\n```json\n", "").replace("\n```", ""))
        benchmark = get_sector_benchmark(sector)
    except Exception as e:
        market_data = {"demand_level": "N/A", "market_size_kes": 0, "price_range": {"avg_kes": 0}, "competitor_count": 0}
        ai_json = {"recommendation": "Error", "viability": "N/A", "risk_analysis": str(e), "saturation": "N/A", "pricing_strategy": "N/A"}
        benchmark = {}

    pdf = EvidLensPDF()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'Market Feasibility Report: {q}', 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 6, f'Sector: {sector} | County: {county} | Generated: {datetime.now().strftime("%d %b %Y")}', 0, 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*SECONDARY)
    pdf.cell(0, 8, '1. Executive Summary - Lens AI', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f"Recommendation: {ai_json.get('recommendation')}\n\nViability: {ai_json.get('viability')}\n{ai_json.get('risk_analysis')}")
    pdf.ln(3)
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
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, '3. Risk Analysis & Strategy', 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, f"Saturation: {ai_json.get('saturation')}\nPricing Strategy: {ai_json.get('pricing_strategy')}")
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, 'KRA COMPLIANT REPORT - FOR BUSINESS PLANNING PURPOSES', 0, 1, 'C', 1)
    return pdf.output(dest='S').encode('latin1')

def generate_market_report_excel(db: Session, sector: str, county: str, q: str) -> bytes:
    return b""

generate_report_pdf = generate_market_report_pdf
