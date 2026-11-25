# FILE: app/modules/report_builder/service.py
# VERSION: 2.6.4 PRODUCTION - MERGED
# KEPT FROM 2.6.2: FPDF fallback, S3 save_to_storage, fetch_all_live, AI service, KB benchmark, pricing search, Excel, aliases
# ADDED IN 2.6.4: Global corporate ReportLab cover + KPI cards + Matplotlib charts (bar / donut / county) + real-data-only empty states
# RULE: NO DEMO. NO SEED. NO FAKE 72 / 194. REAL DB ONLY.

import os
import io
import json
import traceback
from datetime import datetime
from datetime import timezone

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

# ReportLab + Matplotlib - corporate - optional, fallback to FPDF if missing
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.platypus import Paragraph
    from reportlab.platypus import Spacer
    from reportlab.platypus import Table
    from reportlab.platypus import TableStyle
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import PageBreak
    HAS_CORPORATE = True
except Exception as _e:
    print(f"Corporate ReportLab not loaded, will use FPDF fallback: {_e}")
    HAS_CORPORATE = False

PRIMARY = (10, 31, 68)
SECONDARY = (20, 184, 166)
ACCENT = (245, 158, 11)
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("S3_REGION", "eu-west-1")
PAGE_W = 190
LEFT = 10
UTC = timezone.utc
REPORTS_DIR = "app/static/reports"

# Corporate colours - only used if ReportLab available
if HAS_CORPORATE:
    NAVY = colors.HexColor("#0A1F44")
    NAVY_LIGHT = colors.HexColor("#0F2340")
    TEAL = colors.HexColor("#14B8A6")
    TEAL_DARK = colors.HexColor("#0D9488")
    GOLD = colors.HexColor("#C5A880")
    GREY_BG = colors.HexColor("#F5F7FA")
    GREY_TEXT = colors.HexColor("#64748B")
    GREY_BORDER = colors.HexColor("#E2E8F0")
    GREEN = colors.HexColor("#16A34A")
    AMBER = colors.HexColor("#F59E0B")
    RED = colors.HexColor("#DC2626")
    WHITE = colors.white
    BLACK = colors.HexColor("#0F172A")

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
    s = s.replace("\n", " | ")
    s = s.replace("\r", " ")
    return s.encode("latin-1", "ignore").decode("latin-1")

def short(s, n=150):
    txt = safe(s)
    txt = " ".join(txt.split())
    if len(txt) > n:
        txt = txt[:n]
    return txt

def _safe_float(v, default=0.0):
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default

def _fmt_kes(v):
    try:
        return f"KES {float(v):,.0f}"
    except Exception:
        return "KES 0"

def _clean(v, default=""):
    if v is None:
        return default
    s = str(v).strip()
    if s == "":
        return default
    return s

def save_to_storage(local_path: str) -> str:
    if not S3_BUCKET:
        return local_path
    try:
        import boto3
        s3 = boto3.client("s3", region_name=S3_REGION, aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"))
        key = f"reports/{os.path.basename(local_path)}"
        s3.upload_file(local_path, S3_BUCKET, key)
        print(f"S3 backup OK: {key}")
    except Exception as e:
        print(f"S3 backup skipped, local still works: {e}")
    return local_path

class EvidLensPDF(FPDF):
    def header(self):
        try:
            self.set_fill_color(*PRIMARY)
            self.rect(0, 0, 210, 24, 'F')
            self.set_text_color(255, 255, 255)
            self.set_font('Arial', 'B', 14)
            self.set_x(LEFT)
            self.cell(PAGE_W, 8, 'EvidLens', 0, 1, 'L')
            self.set_font('Arial', '', 8)
            self.set_x(LEFT)
            self.cell(PAGE_W, 4, 'Kenya Decision Intelligence - 12 Engines LIVE', 0, 1, 'L')
            self.ln(2)
        except Exception as e:
            print(f"header skipped: {e}")
    def footer(self):
        try:
            self.set_y(-15)
            self.set_text_color(100, 100, 100)
            self.set_font('Arial', 'I', 7)
            self.set_x(LEFT)
            txt = f'app.evidlens.co.ke | Page {self.page_no()} | {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            self.cell(PAGE_W, 10, safe(txt), 0, 0, 'C')
        except Exception as e:
            print(f"footer skipped: {e}")

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
        return {"competitors": competitors, "prices": prices, "demand": demand, "companies": companies, "news": news, "social": social, "knowledge": knowledge, "exports": exports}

def _safe_write(pdf, fn):
    try:
        pdf.set_x(LEFT)
        fn()
    except Exception as e:
        print(f"PDF write skipped: {e}")
        try:
            pdf.set_x(LEFT)
            pdf.ln(4)
        except Exception:
            pass

def _section_title(pdf, text):
    def _do():
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(*SECONDARY)
        pdf.multi_cell(PAGE_W, 7, short(text, 150))
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 9)
    _safe_write(pdf, _do)

def _body(pdf, text):
    def _do():
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(PAGE_W, 5, short(text, 600))
    _safe_write(pdf, _do)

def _bullet(pdf, text):
    def _do():
        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(PAGE_W, 4, short(text, 150))
    _safe_write(pdf, _do)

def _fallback_pdf(path: str, q: str, sector: str, location: str, budget: str):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_x(10)
    pdf.multi_cell(190, 9, short(f'Market Feasibility Report: {q}', 150))
    pdf.set_font('Arial', '', 10)
    pdf.set_x(10)
    pdf.multi_cell(190, 6, short(f'Sector: {sector} | Location: {location} | Budget: KES {budget or "N/A"}', 150))
    pdf.set_x(10)
    pdf.multi_cell(190, 6, short('Report generated on app.evidlens.co.ke. Full 12-engine data was unavailable, this is a fallback report.', 200))
    pdf.output(path)
    return path

# ============================================================
# CORPORATE - CHARTS - NEW 2.6.4
# ============================================================

def _chart_price_bar(prices, demand):
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    seen = {}
    for p in prices[:8]:
        n = _clean(getattr(p, "product_name", "") or getattr(p, "product", ""), "Product")
        if n not in seen:
            seen[n] = _safe_float(getattr(p, "price", 0) or getattr(p, "avg_price_kes", 0))
    for d in demand[:8]:
        n = _clean(getattr(d, "product", ""), "")
        if n and n not in seen:
            seen[n] = _safe_float(getattr(d, "avg_price_kes", 0))
    labels = [k[:18] for k in list(seen.keys())[:8]]
    values = list(seen.values())[:8]
    if not labels:
        ax.text(0.5, 0.5, "No live price data yet\nReal KPIN prices collected at 03:00 EAT daily", ha="center", va="center", fontsize=10, color="#64748B")
        ax.set_xticks([])
        ax.set_yticks([])
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    x = range(len(labels))
    bars = ax.bar(x, values, color="#0A1F44", edgecolor="white", linewidth=0.8, width=0.62, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02, f"{val:,.0f}", ha="center", va="bottom", fontsize=8, color="#0A1F44", weight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8, color="#334155", rotation=18, ha="right")
    ax.set_ylabel("KES", fontsize=9, color="#64748B")
    ax.set_title("Average Price by Product (KES) - Live KPIN Data", fontsize=11, color="#0A1F44", weight="bold", loc="left", pad=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:,.0f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf

def _chart_demand_donut(demand):
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    fig.patch.set_facecolor("white")
    high = sum(1 for m in demand if _safe_float(getattr(m, "demand_score", 0)) >= 70)
    med = sum(1 for m in demand if 40 <= _safe_float(getattr(m, "demand_score", 0)) < 70)
    low = sum(1 for m in demand if _safe_float(getattr(m, "demand_score", 0)) < 40)
    total = high + med + low
    if total == 0:
        ax.text(0.5, 0.5, "No live\ndemand data yet", ha="center", va="center", fontsize=10, color="#64748B")
        ax.set_xticks([])
        ax.set_yticks([])
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    vals = [high, med, low]
    cols = ["#0A1F44", "#14B8A6", "#CBD5E1"]
    labs = [f"High (70+) - {high}", f"Medium (40-69) - {med}", f"Low (<40) - {low}"]
    wedges, _ = ax.pie(vals, colors=cols, startangle=90, counterclock=False, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
    ax.legend(wedges, labs, loc="center", bbox_to_anchor=(0.5, -0.12), fontsize=8, frameon=False, ncol=1)
    ax.set_title("Demand Distribution", fontsize=11, color="#0A1F44", weight="bold", pad=10)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf

def _chart_county_bar(demand):
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    by = {}
    for m in demand:
        c = _clean(getattr(m, "county", ""), "Kenya")
        by.setdefault(c, []).append(_safe_float(getattr(m, "avg_price_kes", 0)))
    labels = []
    values = []
    for c, arr in list(by.items())[:7]:
        if arr:
            labels.append(c)
            values.append(sum(arr) / len(arr))
    if not labels:
        ax.text(0.5, 0.5, "No live county data yet", ha="center", va="center", fontsize=10, color="#64748B")
        ax.set_xticks([])
        ax.set_yticks([])
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    y = range(len(labels))
    ax.barh(y, values, color="#14B8A6", edgecolor="white", height=0.55)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9, color="#334155")
    ax.invert_yaxis()
    ax.set_xlabel("Avg Price KES", fontsize=9, color="#64748B")
    ax.set_title("Average Price by County (KES)", fontsize=11, color="#0A1F44", weight="bold", loc="left", pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf

# ============================================================
# CORPORATE PDF - NEW 2.6.4 - USES fetch_all_live + KB + AI
# ============================================================

def _corporate_pdf(path, q, sector, country, county, sub_county, ward, town, budget, plan_name, location, live):
    ss = getSampleStyleSheet()
    S_title = ParagraphStyle("CorpTitle", parent=ss["Title"], fontSize=32, leading=36, textColor=NAVY, alignment=TA_LEFT, fontName="Helvetica-Bold", spaceAfter=6)
    S_sub = ParagraphStyle("CorpSub", parent=ss["Normal"], fontSize=13, leading=18, textColor=GREY_TEXT, alignment=TA_LEFT, fontName="Helvetica", spaceAfter=4)
    S_h1 = ParagraphStyle("CorpH1", parent=ss["Heading1"], fontSize=18, leading=22, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8, keepWithNext=True)
    S_h2 = ParagraphStyle("CorpH2", parent=ss["Heading2"], fontSize=13, leading=17, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6, keepWithNext=True)
    S_body = ParagraphStyle("CorpBody", parent=ss["Normal"], fontSize=10, leading=15, textColor=BLACK, fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6)
    S_small = ParagraphStyle("CorpSmall", parent=ss["Normal"], fontSize=9, leading=13, textColor=BLACK, fontName="Helvetica", alignment=TA_LEFT, spaceAfter=4)
    S_bullet = ParagraphStyle("CorpBullet", parent=S_body, leftIndent=14, firstLineIndent=0, bulletIndent=6, spaceAfter=4, alignment=TA_LEFT)
    S_caption = ParagraphStyle("CorpCap", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=8)
    S_kpi_l = ParagraphStyle("KpiL", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY_TEXT, fontName="Helvetica-Bold", alignment=TA_CENTER)
    S_kpi_v = ParagraphStyle("KpiV", parent=ss["Normal"], fontSize=20, leading=22, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_CENTER)
    S_kpi_s = ParagraphStyle("KpiS", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY_TEXT, fontName="Helvetica", alignment=TA_CENTER)
    S_cell = ParagraphStyle("Cell", parent=ss["Normal"], fontSize=9, leading=12, textColor=BLACK, fontName="Helvetica", alignment=TA_LEFT)
    S_cell_r = ParagraphStyle("CellR", parent=S_cell, alignment=TA_RIGHT)
    S_th = ParagraphStyle("TH", parent=ss["Normal"], fontSize=8.5, leading=11, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_LEFT)
    S_th_r = ParagraphStyle("THR", parent=S_th, alignment=TA_RIGHT)

    def _hf(canvas, doc):
        canvas.saveState()
        if doc.page == 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, A4[1] - 18 * mm, A4[0], 18 * mm, stroke=0, fill=1)
            canvas.setFillColor(WHITE)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(18 * mm, A4[1] - 11 * mm, "EvidLens")
            canvas.setFont("Helvetica", 8)
            canvas.drawString(18 * mm, A4[1] - 15 * mm, "Kenya Decision Intelligence  |  12 Engines LIVE")
            canvas.setFillColor(GOLD)
            canvas.setFont("Helvetica-Bold", 8)
            canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 11 * mm, "CONFIDENTIAL")
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(WHITE)
            canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 15 * mm, "For Investment Decision Use")
        else:
            canvas.setStrokeColor(GOLD)
            canvas.setLineWidth(2.5)
            canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        canvas.setFillColor(GREY_TEXT)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(A4[0] / 2, 14 * mm, f"EvidLens  |  Decision Intelligence for Kenya  |  Confidential  |  Page {doc.page}")
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(A4[0] / 2, 10 * mm, "app.evidlens.co.ke  |  Source: KPIN + Live DB  |  Generated from live data only - no demo data")
        canvas.restoreState()

    demand = live["demand"]
    prices = live["prices"]
    companies = live["companies"]
    competitors = live["competitors"]
    news = live["news"]
    social = live["social"]
    knowledge = live["knowledge"]
    exports = live["exports"]
    has_data = len(demand) > 0 or len(prices) > 0 or len(companies) > 0
    if demand:
        avg_price = sum(_safe_float(getattr(m, "avg_price_kes", 0)) for m in demand) / len(demand)
        avg_demand = sum(_safe_float(getattr(m, "demand_score", 0)) for m in demand) / len(demand)
        max_price = max(_safe_float(getattr(m, "avg_price_kes", 0)) for m in demand)
        min_price = min(_safe_float(getattr(m, "avg_price_kes", 0)) for m in demand)
    elif prices:
        vals = [_safe_float(getattr(p, "price", 0)) for p in prices]
        avg_price = sum(vals) / len(vals) if vals else 0
        avg_demand = 0
        max_price = max(vals) if vals else 0
        min_price = min(vals) if vals else 0
    else:
        avg_price = 0
        avg_demand = 0
        max_price = 0
        min_price = 0
    # KB benchmark - KEPT FROM 2.6.2 - try, never crash
    benchmark = {}
    try:
        with Session(engine) as _db:
            benchmark = get_sector_benchmark(_db, sector) or {}
    except Exception:
        benchmark = {}
    # AI - KEPT - try, never crash
    ai_text = ""
    try:
        if ai_service is not None and hasattr(ai_service, "generate_insight"):
            ai_text = str(ai_service.generate_insight(q, sector, county) or "")
    except Exception:
        ai_text = ""
    if not has_data:
        verdict = "INSUFFICIENT LIVE DATA - DO NOT INVEST ON THIS REPORT ALONE"
        vcolor = AMBER
        vtext = "No live KPIN records were found for this sector / county at generation time. This report shows an honest empty state. Wait for the 03:00 EAT KPIN collection, then regenerate. Do not use seed or demo values."
    elif avg_demand >= 70 and len(competitors) < 10:
        verdict = "GO - ATTRACTIVE - LOW COMPETITION, HIGH DEMAND"
        vcolor = GREEN
        vtext = f"Live demand {_fmt_kes(avg_price)} avg price, demand {avg_demand:.0f}/100, only {len(competitors)} competitors. Validate with 20+ customer interviews before committing capital."
    elif avg_demand >= 50:
        verdict = "CONDITIONAL GO - VALIDATE BEFORE SCALING"
        vcolor = AMBER
        vtext = f"Live demand moderate {avg_demand:.0f}/100, avg price {_fmt_kes(avg_price)}, {len(competitors)} competitors. Start small, test price, scale after 30 days of real sales."
    else:
        verdict = "HOLD - LOW LIVE DEMAND"
        vcolor = RED
        vtext = f"Live demand low {avg_demand:.0f}/100. Do not commit large capital yet. Re-check after next KPIN collection."

    story = []
    now_str = datetime.now().strftime("%d %b %Y %H:%M EAT")
    story.append(Spacer(1, 22 * mm))
    story.append(Paragraph("MARKET FEASIBILITY", ParagraphStyle("Eyebrow", parent=S_sub, fontSize=10, leading=12, textColor=TEAL_DARK, fontName="Helvetica-Bold")))
    story.append(Paragraph("Market Feasibility Report", S_title))
    story.append(Paragraph(f"{safe(q)} &nbsp;|&nbsp; {safe(sector)}", ParagraphStyle("Sub2", parent=S_sub, fontSize=16, leading=20, textColor=NAVY, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"Location: {safe(location)} &nbsp;•&nbsp; Country: {safe(country)} &nbsp;•&nbsp; County: {safe(county) or 'All Counties'}", S_sub))
    story.append(Paragraph(f"Budget: KES {safe(budget) or 'Not specified'} &nbsp;•&nbsp; Plan: {safe(plan_name)} &nbsp;•&nbsp; Generated: {now_str}", S_sub))
    story.append(Spacer(1, 6 * mm))
    div = Table([[""]], colWidths=[170 * mm])
    div.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 2.5, GOLD), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(div)
    story.append(Paragraph("EvidLens Kenya Decision Intelligence", ParagraphStyle("Brand", parent=S_sub, fontSize=11, leading=14, textColor=NAVY, fontName="Helvetica-Bold")))
    story.append(Paragraph("12 Engines &nbsp;•&nbsp; Competitive &nbsp;•&nbsp; Pricing &nbsp;•&nbsp; Demand &nbsp;•&nbsp; Location &nbsp;•&nbsp; Consumer &nbsp;•&nbsp; Risk &nbsp;•&nbsp; Policy &nbsp;•&nbsp; Funding &nbsp;•&nbsp; Export &nbsp;•&nbsp; Knowledge &nbsp;•&nbsp; AI Insights", ParagraphStyle("Eng", parent=S_sub, fontSize=8.5, leading=12, textColor=GREY_TEXT)))
    story.append(Spacer(1, 8 * mm))
    vt = Table([[Paragraph("<b>INVESTMENT VERDICT</b>", ParagraphStyle("VL", parent=S_small, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_LEFT)), Paragraph(f"<b>{verdict}</b>", ParagraphStyle("VV", parent=S_small, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_LEFT))]], colWidths=[38 * mm, 132 * mm])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), vcolor), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(vt)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(vtext, S_body))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("How to use this report - Start with Executive Summary (p.2), then Pricing & Demand charts (p.3), then Risks & Action Plan (p.5-6). All figures are from live DB rows at generation time. If a section says 'No live data', it means no real KPIN row existed - it is not filled with demo values.", S_small))
    if benchmark:
        story.append(Paragraph(f"Sector Benchmark (Knowledge Base): {safe(str(benchmark)[:300])}", S_small))
    if ai_text:
        story.append(Paragraph(f"AI Insight: {safe(ai_text[:400])}", S_small))
    story.append(Paragraph("CONFIDENTIAL • Prepared for the requesting user • EvidLens does not provide legal / tax advice. Validate with KRA, CBK and county licensing before committing capital.", ParagraphStyle("Cap", parent=S_small, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER)))

    story.append(PageBreak())
    story.append(Paragraph("1 &nbsp; Executive Summary", S_h1))
    story.append(Paragraph(f"This report assesses <b>{safe(q)}</b> in <b>{safe(location)}</b> for <b>{safe(sector)}</b>. Based on <b>{len(prices) + len(demand)} live price / metric records</b>, <b>{len(companies)} companies</b>, <b>{len(competitors)} competitors</b>, <b>{len(news)} risk signals</b> and <b>{len(social)} consumer mentions</b>.", S_body))
    if not has_data:
        story.append(Paragraph("No live market data was available for this exact filter. Charts below show an honest empty state. Regenerate after next KPIN collection or broaden county / sector.", S_body))
    kpi = []
    kpi.append([Paragraph("AVG PRICE", S_kpi_l), Paragraph("AVG DEMAND", S_kpi_l), Paragraph("COMPETITORS", S_kpi_l), Paragraph("PRICE RECORDS", S_kpi_l)])
    kpi.append([Paragraph(_fmt_kes(avg_price) if has_data else "—", S_kpi_v), Paragraph(f"{avg_demand:.0f} / 100" if has_data else "—", S_kpi_v), Paragraph(str(len(competitors)), S_kpi_v), Paragraph(str(len(prices) + len(demand)), S_kpi_v)])
    kpi.append([Paragraph(f"Range {_fmt_kes(min_price)} - {_fmt_kes(max_price)}" if has_data else "No live data", S_kpi_s), Paragraph("Live demand score" if has_data else "No live data", S_kpi_s), Paragraph("Tracked in DB" if has_data else "No live data", S_kpi_s), Paragraph("KPIN + MarketMetric" if has_data else "No live data", S_kpi_s)])
    kt = Table(kpi, colWidths=[42.5 * mm, 42.5 * mm, 42.5 * mm, 42.5 * mm])
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREY_BG), ("BOX", (0, 0), (-1, -1), 0.6, GREY_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story.append(kt)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Key Findings", S_h2))
    if has_data:
        story.append(Paragraph(f"• &nbsp; Avg live price <b>{_fmt_kes(avg_price)}</b> (range {_fmt_kes(min_price)} - {_fmt_kes(max_price)}). Use median for pricing.", S_bullet))
        story.append(Paragraph(f"• &nbsp; Avg live demand <b>{avg_demand:.0f} / 100</b>. Above 70 + few competitors = attractive; below 40 = hold.", S_bullet))
        story.append(Paragraph(f"• &nbsp; <b>{len(competitors)} competitors</b> tracked. See Section 4.", S_bullet))
    else:
        story.append(Paragraph("• &nbsp; No live findings yet - see empty-state note above.", S_bullet))

    story.append(Paragraph("2 &nbsp; Pricing Engine (Price Oracle)", S_h1))
    story.append(Paragraph("Live prices from KPIN and MarketMetric. No smoothing, no demo fallback.", S_body))
    try:
        story.append(RLImage(_chart_price_bar(prices, demand), width=170 * mm, height=75 * mm))
        story.append(Paragraph("Figure 1 - Average price by product (KES). Source: Live DB at generation time.", ParagraphStyle("Cap2", parent=S_small, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER)))
    except Exception:
        traceback.print_exc()
    pr_rows = [[Paragraph("Product", S_th), Paragraph("County", S_th), Paragraph("Price", S_th_r), Paragraph("Demand", S_th_r)]]
    comb = []
    for m in demand[:15]:
        comb.append((_clean(getattr(m, "product", ""), "Product"), _clean(getattr(m, "county", ""), "Kenya"), _safe_float(getattr(m, "avg_price_kes", 0)), _safe_float(getattr(m, "demand_score", 0))))
    for p in prices[:10]:
        if len(comb) >= 15:
            break
        comb.append((_clean(getattr(p, "product_name", ""), "Product"), _clean(getattr(p, "county", ""), "Kenya"), _safe_float(getattr(p, "price", 0)), 0))
    if not comb:
        pr_rows.append([Paragraph("No live price data yet", S_cell), Paragraph("—", S_cell), Paragraph("—", S_cell_r), Paragraph("—", S_cell_r)])
    else:
        for prod, cty, pr, dm in comb:
            pr_rows.append([Paragraph(prod, S_cell), Paragraph(cty, S_cell), Paragraph(_fmt_kes(pr), S_cell_r), Paragraph(f"{dm:.0f} / 100" if dm else "—", S_cell_r)])
    pt = Table(pr_rows, colWidths=[68 * mm, 34 * mm, 34 * mm, 34 * mm], repeatRows=1)
    pt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story.append(pt)

    story.append(Paragraph("3 &nbsp; Demand Radar", S_h1))
    try:
        dt = Table([[RLImage(_chart_demand_donut(demand), width=85 * mm, height=75 * mm)]], colWidths=[170 * mm])
        dt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(dt)
        story.append(Paragraph("Figure 2 - Demand distribution: High (70+), Medium (40-69), Low (<40).", ParagraphStyle("Cap3", parent=S_small, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER)))
        story.append(RLImage(_chart_county_bar(demand), width=170 * mm, height=66 * mm))
        story.append(Paragraph("Figure 3 - Average price by county (KES). Buy low county, sell high county, minus transport.", ParagraphStyle("Cap4", parent=S_small, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER)))
    except Exception:
        traceback.print_exc()

    story.append(Paragraph("4 &nbsp; Competitive Engine", S_h1))
    if not competitors and not companies:
        story.append(Paragraph("No competitors tracked for this exact filter. That does not mean zero competition - check wider county / sector in dashboard.", S_body))
    else:
        story.append(Paragraph(f"{len(competitors)} competitors + {len(companies)} companies found. Live list below.", S_body))
        cr = [[Paragraph("Company", S_th), Paragraph("Sector", S_th), Paragraph("County", S_th), Paragraph("Rating", S_th_r)]]
        for c in list(competitors)[:10] + list(companies)[:10]:
            cr.append([Paragraph(_clean(getattr(c, "name", ""), "Company"), S_cell), Paragraph(_clean(getattr(c, "sector", ""), ""), S_cell), Paragraph(_clean(getattr(c, "county", ""), ""), S_cell), Paragraph(f"{_safe_float(getattr(c, 'rating', 0)):.1f}" if _safe_float(getattr(c, "rating", 0)) else "—", S_cell_r)])
        ct = Table(cr, colWidths=[58 * mm, 58 * mm, 28 * mm, 26 * mm], repeatRows=1)
        ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
        story.append(ct)

    story.append(Paragraph("5 &nbsp; Location Engine (County Mapper)", S_h1))
    story.append(Paragraph(f"Focus: <b>{safe(location)}</b> | County: {safe(county)} | SubCounty: {safe(sub_county)} | Ward: {safe(ward)} | Town: {safe(town)} | Coverage: {len(companies)} companies mapped.", S_body))
    story.append(Paragraph("Site checklist: Foot traffic 7am / 12pm / 6pm for 3 days. Nearest competitor distance. Transport cost. Rent + goodwill vs 3 months revenue at median price. County permit + health / fire if food.", S_body))

    story.append(Paragraph("6 &nbsp; Consumer Engine (Consumer Pulse)", S_h1))
    if not social:
        story.append(Paragraph("• &nbsp; No consumer mentions yet.", S_bullet))
    for s in social[:10]:
        story.append(Paragraph(f"• &nbsp; [{safe(getattr(s, 'platform', 'X'))} {safe(getattr(s, 'sentiment', 'neutral'))}]: {safe(str(getattr(s, 'content', ''))[:120])}", S_bullet))
    story.append(Paragraph("7 &nbsp; Core OS (Risk Sentinel)", S_h1))
    if not news:
        story.append(Paragraph("• &nbsp; No alerts.", S_bullet))
    for n in news[:8]:
        story.append(Paragraph(f"• &nbsp; {safe(getattr(n, 'title', 'News'))}: {safe(str(getattr(n, 'summary', ''))[:120])}", S_bullet))
    story.append(Paragraph("8 &nbsp; Regulatory Engine (Policy Watch)", S_h1))
    if plan_name != "Enterprise":
        story.append(Paragraph("[Upgrade to Enterprise to unlock full Regulatory Engine data]", S_small))
    for k in knowledge[:8]:
        story.append(Paragraph(f"• &nbsp; {safe(getattr(k, 'sector', 'Policy'))} | {safe(str(getattr(k, 'chunk_text', ''))[:120])}", S_bullet))
    story.append(Paragraph("9 &nbsp; Core OS (Funding Radar)", S_h1))
    story.append(Paragraph(f"Budget: KES {safe(budget) or 'Not provided'} | For {safe(q)} in {safe(sector)}/{safe(county)}: SME funding - Kenya Uwezo Fund, Youth Fund, SACCO loans, Bank SME. Working capital = 30% inventory + licenses.", S_body))
    story.append(Paragraph("10 &nbsp; Business OS (Export Navigator)", S_h1))
    if plan_name != "Enterprise":
        story.append(Paragraph("[Enterprise plan unlocks full Export Navigator]", S_small))
    for e in exports[:8]:
        story.append(Paragraph(f"• &nbsp; {safe(getattr(e, 'product', 'Product'))} -> {safe(getattr(e, 'country', 'Country'))} | Score {safe(getattr(e, 'opportunity_score', 0))}", S_bullet))
    story.append(Paragraph("11 &nbsp; Core OS (Knowledge Base)", S_h1))
    if not knowledge:
        story.append(Paragraph("• &nbsp; No knowledge records yet.", S_bullet))
    for k in knowledge[:8]:
        story.append(Paragraph(f"• &nbsp; {safe(str(getattr(k, 'chunk_text', ''))[:120])}", S_bullet))
    story.append(Paragraph("12 &nbsp; AI Insights + Report Builder - Verdict", S_h1))
    story.append(Paragraph(f"<b>{verdict}</b> - {vtext}", S_body))
    if ai_text:
        story.append(Paragraph(f"AI Insight: {safe(ai_text[:600])}", S_body))
    story.append(Paragraph(f"FINAL VERDICT for {safe(q)} in {safe(location)}: Sector {safe(sector)} has {len(competitors)} competitors, {len(prices)} price points, {len(demand)} demand signals. Consumer {len(social)} mentions, Risk {len(news)} alerts. Budget KES {safe(budget)}, recommended entry: Source from {safe(county)} suppliers, price at median, target {safe(sub_county or county)} first. Regulatory: {len(knowledge)} policies. Export: {len(exports)} routes. Plan {safe(plan_name)}.", S_body))
    story.append(Paragraph("30-Day Action Plan: Week 1 - Interview 20 customers. Week 2 - Sell small batch at median price. Week 3 - Fix one variable only. Week 4 - Decide: scale if net profit covers rent + transport + time, else pivot.", S_body))
    story.append(Paragraph("Disclaimer: For information only, not investment / legal / tax advice. Prices change daily. Verify on the ground before committing capital.", ParagraphStyle("Disc", parent=S_small, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER)))

    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm, title=f"EvidLens - {safe(q)} - {safe(location)}", author="EvidLens")
    doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
    return path

# ============================================================
# MAIN ENTRY - KEEPS 2.6.2 SIGNATURE
# ============================================================

def generate_market_report_pdf_file(q: str, sector: str, country: str = "Kenya", county: str = None, sub_county: str = None, ward: str = None, town: str = None, budget: str = None, plan_name: str = "Pro") -> str:
    location = town or ward or sub_county or county or country
    os.makedirs("app/static/reports", exist_ok=True)
    fname = f"EvidLens_{safe(q).replace(' ', '_')}_{safe(county or 'Kenya')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    fname = "".join(c for c in fname if c.isalnum() or c in "._-")
    path = f"app/static/reports/{fname}"
    try:
        live = fetch_all_live(sector, county, q)
        if HAS_CORPORATE:
            try:
                return save_to_storage(_corporate_pdf(path, q, sector, country, county, sub_county, ward, town, budget, plan_name, location, live))
            except Exception as e:
                print(f"Corporate PDF failed, falling back to FPDF: {e}")
                traceback.print_exc()
        # FPDF fallback - KEPT FROM 2.6.2 - same 12 sections as before
        pdf = EvidLensPDF()
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 15)
        pdf.set_x(LEFT)
        pdf.multi_cell(PAGE_W, 9, short(f'Market Feasibility Report: {q}', 150))
        pdf.set_font('Arial', '', 9)
        pdf.set_x(LEFT)
        pdf.multi_cell(PAGE_W, 6, short(f'Sector: {sector} | Location: {location} | Budget: KES {budget or "N/A"} | Plan: {plan_name} | {datetime.now().strftime("%d %b %Y %H:%M")}', 150))
        pdf.ln(4)
        _section_title(pdf, '1. Quick Business Analysis Input')
        _body(pdf, f"Product: {q} | Sector: {sector} | Country: {country} | County: {county} | SubCounty: {sub_county} | Ward: {ward} | Town: {town} | Budget: KES {budget} | Location: {location}")
        pdf.ln(3)
        _section_title(pdf, f'2. Competitive Engine - {len(live["competitors"])} Records')
        if not live["competitors"]:
            _bullet(pdf, "No competitors yet. No live data - not seed.")
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
        _body(pdf, f"Analysis location: {location} | County: {county} | SubCounty: {sub_county} | Ward: {ward} | Town: {town} | Coverage: {len(live['companies'])} companies mapped.")
        pdf.ln(3)
        _section_title(pdf, f'6. Consumer Engine (Consumer Pulse) - {len(live["social"])} Mentions')
        if not live["social"]:
            _bullet(pdf, "No consumer mentions yet.")
        for s in live["social"][:10]:
            plat = getattr(s, 'platform', 'X')
            sent = getattr(s, 'sentiment', 'neutral')
            cont = str(getattr(s, 'content', ''))[:100]
            _bullet(pdf, f"- [{plat} {sent}]: {cont}")
        pdf.ln(3)
        _section_title(pdf, f'7. Core OS (Risk Sentinel) - {len(live["news"])} Alerts')
        if not live["news"]:
            _bullet(pdf, "No alerts.")
        for n in live["news"][:8]:
            _bullet(pdf, f"- {getattr(n, 'title', 'News')}: {str(getattr(n, 'summary', ''))[:100]}")
        pdf.ln(3)
        _section_title(pdf, f'8. Regulatory Engine (Policy Watch) - {len(live["knowledge"])} Policies')
        if plan_name != "Enterprise":
            pdf.set_font('Arial', 'I', 8)
            pdf.set_x(LEFT)
            pdf.multi_cell(PAGE_W, 5, short("[Upgrade to Enterprise to unlock full Regulatory Engine data]"))
            pdf.set_font('Arial', '', 8)
        for k in live["knowledge"][:8]:
            _bullet(pdf, f"- {getattr(k, 'sector', 'Policy')} | {str(getattr(k, 'chunk_text', ''))[:100]}")
        pdf.ln(3)
        _section_title(pdf, '9. Core OS (Funding Radar)')
        _body(pdf, f"Budget: KES {budget or 'Not provided'} | For {q} in {sector}/{county}: SME funding - Kenya Uwezo Fund, Youth Fund, SACCO loans, Bank SME. Working capital = 30% inventory + licenses.")
        pdf.ln(3)
        _section_title(pdf, f'10. Business OS (Export Navigator) - {len(live["exports"])} Opportunities')
        if plan_name != "Enterprise":
            pdf.set_font('Arial', 'I', 8)
            pdf.set_x(LEFT)
            pdf.multi_cell(PAGE_W, 5, short("[Enterprise plan unlocks full Export Navigator]"))
            pdf.set_font('Arial', '', 8)
        for e in live["exports"][:8]:
            _bullet(pdf, f"- {getattr(e, 'product', 'Product')} -> {getattr(e, 'country', 'Country')} | Score {getattr(e, 'opportunity_score', 0)}")
        pdf.ln(3)
        _section_title(pdf, f'11. Core OS (Knowledge Base) - {len(live["knowledge"])} Records')
        if not live["knowledge"]:
            _bullet(pdf, "No knowledge records yet.")
        for k in live["knowledge"][:8]:
            _bullet(pdf, f"- {str(getattr(k, 'chunk_text', ''))[:100]}")
        pdf.ln(3)
        _section_title(pdf, '12. AI Insights + Report Builder - Verdict')
        _body(pdf, f"FINAL VERDICT for {q} in {location}: Sector {sector} has {len(live['competitors'])} competitors, {len(live['prices'])} price points, {len(live['demand'])} demand signals. Consumer Pulse {len(live['social'])} mentions, Risk Sentinel {len(live['news'])} alerts. With budget KES {budget}, recommended entry: Source from {county} suppliers, price at median observed, target {sub_county or county} first. Regulatory: {len(live['knowledge'])} policies. Export: {len(live['exports'])} routes. Plan {plan_name} - This PDF aggregates ALL 12 engines LIVE from app.evidlens.co.ke")
        pdf.output(path)
        return save_to_storage(path)
    except Exception as e:
        print(f"Main PDF failed, using fallback: {e}")
        traceback.print_exc()
        return save_to_storage(_fallback_pdf(path, q, sector, location, budget))

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
        rows = [("Query", q or ""), ("Sector", sector or ""), ("Country", country or ""), ("County", county or ""), ("SubCounty", sub_county or ""), ("Ward", ward or ""), ("Town", town or ""), ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M"))]
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
        return save_to_storage(path)
    except Exception as e:
        print(f"Excel failed {e}")
        traceback.print_exc()
        os.makedirs("app/static/reports", exist_ok=True)
        path = f"app/static/reports/EvidLens_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Query,{q}\nSector,{sector}\nCounty,{county}\nError,{e}\n")
        return path

generate_report_pdf = generate_market_report_pdf
generate_pdf_path = generate_market_report_pdf_file
