import os
import io
import traceback
from datetime import datetime
from datetime import timezone
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
    print(f"Corporate ReportLab not loaded: {_e}")
    HAS_CORPORATE = False
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_REGION = os.getenv("S3_REGION", "eu-west-1")
UTC = timezone.utc
REPORTS_DIR = "app/static/reports"
LOGO_PATH = "app/static/logo.png"
SERIES_MAP = {
    "EXEC_BRIEF": "ExecBrief",
    "MARKET_FEASIBILITY": "MarketIntelligence",
    "INDUSTRY_OUTLOOK": "IndustryOutlook",
    "SECTOR_PULSE": "SectorPulse",
    "CONSUMER_ANALYSIS": "ConsumerInsights",
    "PRODUCT_WATCH": "ProductWatch",
    "INVESTOR_PITCH": "InvestorPitch",
    "BUSINESS_PLAN": "BusinessPlan",
    "KRA_TAX": "KRATax",
}
TITLE_MAP = {
    "EXEC_BRIEF": "Executive Intelligence Brief",
    "MARKET_FEASIBILITY": "Market Feasibility Report",
    "INDUSTRY_OUTLOOK": "Industry Outlook",
    "SECTOR_PULSE": "Sector Pulse",
    "CONSUMER_ANALYSIS": "Consumer Insights Report",
    "PRODUCT_WATCH": "Product Watch",
    "INVESTOR_PITCH": "Investor Pitch Deck",
    "BUSINESS_PLAN": "Business Plan - Bank Loan Pack",
    "KRA_TAX": "KRA Tax Report",
}
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
    SLATE = colors.HexColor("#334155")
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
def _build_filename(series, topic, geography, ext="pdf"):
    def clean(s):
        s = safe(str(s or "")).replace(" ", "")
        s = "".join(c for c in s if c.isalnum() or c in "-_")
        return s[:40] or "Kenya"
    year = datetime.now().strftime("%Y")
    return f"EvidLens_{clean(series)}_{clean(topic)}_{clean(geography)}_{year}_v1.0.{ext}"
def _build_path(report_type, q, county, town, ward, sub_county, country):
    series = SERIES_MAP.get(report_type, "MarketIntelligence")
    geo = town or ward or sub_county or county or country or "Kenya"
    fname = _build_filename(series, q, geo, "pdf")
    os.makedirs("app/static/reports", exist_ok=True)
    return f"app/static/reports/{fname}"
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
def fetch_all_live(sector: str = None, county: str = None, product: str = None, limit: int = 20):
    with Session(engine) as s:
        def safe_query(model, l=limit):
            try:
                q = select(model)
                if county and hasattr(model, "county"):
                    q = q.where(getattr(model, "county") == county)
                if sector and hasattr(model, "sector"):
                    q = q.where(getattr(model, "sector") == sector)
                q = q.limit(l)
                return s.exec(q).all()
            except Exception as e:
                print(f"fetch {model} failed {e}")
                try:
                    s.rollback()
                except Exception:
                    pass
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
def _chart_price_bar(prices, demand):
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    seen = {}
    for p in prices[:10]:
        n = _clean(getattr(p, "product_name", "") or getattr(p, "product", ""), "Product")
        if n not in seen:
            seen[n] = _safe_float(getattr(p, "price", 0) or getattr(p, "avg_price_kes", 0))
    for d in demand[:10]:
        n = _clean(getattr(d, "product", ""), "")
        if n and n not in seen:
            seen[n] = _safe_float(getattr(d, "avg_price_kes", 0))
    labels = [k[:18] for k in list(seen.keys())[:10]]
    values = list(seen.values())[:10]
    if not labels:
        ax.text(0.5, 0.5, "No live price data yet\nReal KPIN prices collected at 03:00 EAT daily", ha="center", va="center", fontsize=10, color="#64748B")
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ["top", "right", "bottom", "left"]:
            ax.spines[sp].set_visible(False)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    x = range(len(labels))
    bars = ax.bar(x, values, color="#0A1F44", edgecolor="white", linewidth=0.8, width=0.62, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02 if max(values) else 0, f"{val:,.0f}", ha="center", va="bottom", fontsize=8, color="#0A1F44", weight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8, color="#334155", rotation=18, ha="right")
    ax.set_ylabel("KES", fontsize=9, color="#64748B")
    ax.set_ylim(0, max(values) * 1.18 if values and max(values) > 0 else 1)
    ax.set_title("Figure 3.1 - Average Price by Product (KES)", fontsize=11, color="#0A1F44", weight="bold", loc="left", pad=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:,.0f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
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
        plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    vals = [high, med, low]
    cols = ["#0A1F44", "#14B8A6", "#CBD5E1"]
    labs = [f"High (70+) - {high}", f"Medium (40-69) - {med}", f"Low (<40) - {low}"]
    wedges, _ = ax.pie(vals, colors=cols, startangle=90, counterclock=False, wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2))
    ax.legend(wedges, labs, loc="center", bbox_to_anchor=(0.5, -0.12), fontsize=8, frameon=False, ncol=1)
    ax.set_title("Figure 3.2 - Demand Distribution", fontsize=11, color="#0A1F44", weight="bold", pad=10)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
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
    for c, arr in list(by.items())[:10]:
        if arr:
            labels.append(c)
            values.append(sum(arr) / len(arr))
    if not labels:
        ax.text(0.5, 0.5, "No live county data yet", ha="center", va="center", fontsize=10, color="#64748B")
        ax.set_xticks([])
        ax.set_yticks([])
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        plt.close()
        buf.seek(0)
        return buf
    y = range(len(labels))
    ax.barh(y, values, color="#14B8A6", edgecolor="white", height=0.55)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9, color="#334155")
    ax.invert_yaxis()
    ax.set_xlabel("Avg Price KES", fontsize=9, color="#64748B")
    ax.set_xlim(0, max(values) * 1.15 if values and max(values) > 0 else 1)
    ax.set_title("Figure 3.3 - Average Price by County (KES)", fontsize=11, color="#0A1F44", weight="bold", loc="left", pad=10)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf
def _styles():
    ss = getSampleStyleSheet()
    S_title = ParagraphStyle("CorpTitle", parent=ss["Title"], fontSize=30, leading=34, textColor=NAVY, alignment=TA_LEFT, fontName="Helvetica-Bold", spaceAfter=6)
    S_sub = ParagraphStyle("CorpSub", parent=ss["Normal"], fontSize=12, leading=17, textColor=GREY_TEXT, alignment=TA_LEFT, fontName="Helvetica", spaceAfter=4)
    S_h1 = ParagraphStyle("CorpH1", parent=ss["Heading1"], fontSize=17, leading=21, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=8, keepWithNext=True)
    S_h2 = ParagraphStyle("CorpH2", parent=ss["Heading2"], fontSize=12.5, leading=16, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6, keepWithNext=True)
    S_h3 = ParagraphStyle("CorpH3", parent=ss["Heading3"], fontSize=11, leading=14, textColor=NAVY_LIGHT, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
    S_body = ParagraphStyle("CorpBody", parent=ss["Normal"], fontSize=10, leading=15, textColor=BLACK, fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6)
    S_small = ParagraphStyle("CorpSmall", parent=ss["Normal"], fontSize=9, leading=13, textColor=BLACK, fontName="Helvetica", alignment=TA_LEFT, spaceAfter=4)
    S_bullet = ParagraphStyle("CorpBullet", parent=S_body, leftIndent=14, firstLineIndent=0, bulletIndent=6, spaceAfter=4, alignment=TA_LEFT)
    S_note = ParagraphStyle("CorpNote", parent=ss["Normal"], fontSize=8, leading=11, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_LEFT, spaceAfter=6)
    S_cap = ParagraphStyle("CorpCap", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY_TEXT, fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=8)
    S_kpi_l = ParagraphStyle("KpiL", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY_TEXT, fontName="Helvetica-Bold", alignment=TA_CENTER)
    S_kpi_v = ParagraphStyle("KpiV", parent=ss["Normal"], fontSize=20, leading=22, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_CENTER)
    S_kpi_s = ParagraphStyle("KpiS", parent=ss["Normal"], fontSize=8, leading=10, textColor=GREY_TEXT, fontName="Helvetica", alignment=TA_CENTER)
    S_cell = ParagraphStyle("Cell", parent=ss["Normal"], fontSize=9, leading=12, textColor=BLACK, fontName="Helvetica", alignment=TA_LEFT)
    S_cell_r = ParagraphStyle("CellR", parent=S_cell, alignment=TA_RIGHT)
    S_th = ParagraphStyle("TH", parent=ss["Normal"], fontSize=8.5, leading=11, textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_LEFT)
    S_th_r = ParagraphStyle("THR", parent=S_th, alignment=TA_RIGHT)
    return {"title": S_title, "sub": S_sub, "h1": S_h1, "h2": S_h2, "h3": S_h3, "body": S_body, "small": S_small, "bullet": S_bullet, "note": S_note, "cap": S_cap, "kpi_l": S_kpi_l, "kpi_v": S_kpi_v, "kpi_s": S_kpi_s, "cell": S_cell, "cell_r": S_cell_r, "th": S_th, "th_r": S_th_r}
def _hf(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 16 * mm, A4[0], 16 * mm, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(18 * mm, A4[1] - 10 * mm, "EvidLens")
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, A4[1] - 13.5 * mm, "Kenya Decision Intelligence")
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 10 * mm, "CONFIDENTIAL")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(WHITE)
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 13.5 * mm, "For Investment Decision Use")
    else:
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(2)
        canvas.line(18 * mm, A4[1] - 14 * mm, A4[0] - 18 * mm, A4[1] - 14 * mm)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.drawString(18 * mm, A4[1] - 10 * mm, "EvidLens")
        canvas.setFillColor(GREY_TEXT)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 10 * mm, "Kenya Decision Intelligence  |  Live Data Only")
    canvas.setFillColor(GREY_TEXT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(A4[0] / 2, 14 * mm, f"EvidLens  |  Decision Intelligence for Kenya  |  Confidential  |  Page {doc.page}")
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, "app.evidlens.co.ke  |  Source: KPIN + Live DB  |  Generated from live data only - no demo data")
    canvas.restoreState()
def _metrics(live):
    demand = live["demand"]
    prices = live["prices"]
    if demand:
        vals = [_safe_float(getattr(m, "avg_price_kes", 0)) for m in demand]
        avg_price = sum(vals) / len(vals) if vals else 0
        avg_demand = sum(_safe_float(getattr(m, "demand_score", 0)) for m in demand) / len(demand)
        max_price = max(vals) if vals else 0
        min_price = min(vals) if vals else 0
        median_price = sorted(vals)[len(vals) // 2] if vals else 0
    elif prices:
        vals = [_safe_float(getattr(p, "price", 0)) for p in prices]
        avg_price = sum(vals) / len(vals) if vals else 0
        avg_demand = 0
        max_price = max(vals) if vals else 0
        min_price = min(vals) if vals else 0
        median_price = sorted(vals)[len(vals) // 2] if vals else 0
    else:
        avg_price = 0
        avg_demand = 0
        max_price = 0
        min_price = 0
        median_price = 0
    return {"avg_price": avg_price, "avg_demand": avg_demand, "max_price": max_price, "min_price": min_price, "median_price": median_price}
def _verdict(live, m):
    has_data = len(live["demand"]) > 0 or len(live["prices"]) > 0 or len(live["companies"]) > 0
    if not has_data:
        return ("INSUFFICIENT LIVE DATA - DO NOT INVEST ON THIS REPORT ALONE", AMBER, "No live KPIN records were found for this sector and county at generation time. This report presents an honest empty state. The evidence base is insufficient for an investment decision. Wait for the 03:00 EAT KPIN collection, then regenerate. No seed or demo values have been used to fill this report.", has_data)
    if m["avg_demand"] >= 70 and len(live["competitors"]) < 10:
        return ("GO - ATTRACTIVE - LOW COMPETITION, HIGH DEMAND", GREEN, f"The evidence suggests an attractive entry. Live demand is {m['avg_demand']:.0f} out of 100, median price is {_fmt_kes(m['median_price'])}, and only {len(live['competitors'])} competitors were tracked for this filter. Entry is attractive subject to supply validation and customer interviews.", has_data)
    if m["avg_demand"] >= 50:
        return ("CONDITIONAL GO - VALIDATE BEFORE SCALING", AMBER, f"The evidence suggests a conditional entry. Live demand is moderate at {m['avg_demand']:.0f} out of 100, median price is {_fmt_kes(m['median_price'])}, and {len(live['competitors'])} competitors were tracked. A small pilot is recommended before scaling.", has_data)
    return ("HOLD - LOW LIVE DEMAND", RED, f"The evidence suggests holding. Live demand is low at {m['avg_demand']:.0f} out of 100. Large capital commitment is not supported by the current evidence base. Re-check after the next KPIN collection.", has_data)
def _cover(story, S, title, q, sector, location, county, country, budget_str, plan_name, now_str, report_no):
    if os.path.exists(LOGO_PATH):
        try:
            lt = Table([[RLImage(LOGO_PATH, width=32 * mm, height=12 * mm)]], colWidths=[170 * mm])
            lt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
            story.append(lt)
        except Exception:
            story.append(Paragraph("EvidLens", ParagraphStyle("LogoTxt", parent=S["sub"], fontSize=18, leading=20, textColor=NAVY, fontName="Helvetica-Bold")))
    else:
        story.append(Paragraph("EvidLens", ParagraphStyle("LogoTxt2", parent=S["sub"], fontSize=18, leading=20, textColor=NAVY, fontName="Helvetica-Bold")))
    story.append(Paragraph("KENYA  |  DECISION INTELLIGENCE", ParagraphStyle("Eyebrow", parent=S["sub"], fontSize=9, leading=11, textColor=TEAL_DARK, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(title, S["title"]))
    story.append(Paragraph(f"{safe(q)}  |  {safe(sector)}", ParagraphStyle("Sub2", parent=S["sub"], fontSize=15, leading=19, textColor=NAVY, fontName="Helvetica-Bold")))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"Location: {safe(location)}  |  County: {safe(county) or 'All Counties'}  |  Country: {safe(country)}", S["sub"]))
    story.append(Paragraph(f"Report No: {report_no}  |  Budget: {budget_str}  |  Plan: {safe(plan_name)}", S["sub"]))
    story.append(Paragraph(f"Generated: {now_str}  |  app.evidlens.co.ke", S["sub"]))
    story.append(Spacer(1, 5 * mm))
    div = Table([[""]], colWidths=[170 * mm])
    div.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 2.5, GOLD), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(div)
    story.append(Paragraph("EvidLens Kenya Decision Intelligence", ParagraphStyle("Brand", parent=S["sub"], fontSize=10, leading=13, textColor=NAVY, fontName="Helvetica-Bold")))
    story.append(Paragraph("Competitive  •  Pricing  •  Demand  •  Location  •  Consumer  •  Risk  •  Policy  •  Funding  •  Export  •  Knowledge  •  AI Insights", ParagraphStyle("Eng", parent=S["sub"], fontSize=8.5, leading=12, textColor=GREY_TEXT)))
    story.append(Spacer(1, 6 * mm))
def _verdict_box(story, S, verdict, vcolor, vtext):
    vt = Table([[Paragraph("<b>INVESTMENT VERDICT</b>", ParagraphStyle("VL", parent=S["small"], textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_LEFT)), Paragraph(f"<b>{verdict}</b>", ParagraphStyle("VV", parent=S["small"], textColor=WHITE, fontName="Helvetica-Bold", alignment=TA_LEFT))]], colWidths=[38 * mm, 132 * mm])
    vt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), vcolor), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(vt)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(vtext, S["body"]))
    story.append(Spacer(1, 4 * mm))
def _kpi_table(story, S, live, m, has_data):
    kpi = []
    kpi.append([Paragraph("MEDIAN PRICE", S["kpi_l"]), Paragraph("AVG DEMAND", S["kpi_l"]), Paragraph("COMPETITORS", S["kpi_l"]), Paragraph("PRICE RECORDS", S["kpi_l"])])
    kpi.append([Paragraph(_fmt_kes(m["median_price"]) if has_data else "—", S["kpi_v"]), Paragraph(f"{m['avg_demand']:.0f} / 100" if has_data else "—", S["kpi_v"]), Paragraph(str(len(live["competitors"])), S["kpi_v"]), Paragraph(str(len(live["prices"]) + len(live["demand"])), S["kpi_v"])])
    kpi.append([Paragraph(f"Mean {_fmt_kes(m['avg_price'])}" if has_data else "No live data", S["kpi_s"]), Paragraph("Live demand score" if has_data else "No live data", S["kpi_s"]), Paragraph("Tracked in DB" if has_data else "No live data", S["kpi_s"]), Paragraph("KPIN + MarketMetric" if has_data else "No live data", S["kpi_s"])])
    kt = Table(kpi, colWidths=[42.5 * mm, 42.5 * mm, 42.5 * mm, 42.5 * mm])
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREY_BG), ("BOX", (0, 0), (-1, -1), 0.6, GREY_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story.append(kt)
    story.append(Spacer(1, 3 * mm))
def _price_table(story, S, live, limit=20):
    pr_rows = [[Paragraph("Product", S["th"]), Paragraph("County", S["th"]), Paragraph("Price", S["th_r"]), Paragraph("Demand", S["th_r"])]]
    comb = []
    for d in live["demand"][:limit]:
        comb.append((_clean(getattr(d, "product", ""), "Product"), _clean(getattr(d, "county", ""), "Kenya"), _safe_float(getattr(d, "avg_price_kes", 0)), _safe_float(getattr(d, "demand_score", 0))))
    for p in live["prices"][:10]:
        if len(comb) >= limit:
            break
        comb.append((_clean(getattr(p, "product_name", ""), "Product"), _clean(getattr(p, "county", ""), "Kenya"), _safe_float(getattr(p, "price", 0)), 0))
    if not comb:
        pr_rows.append([Paragraph("No live price data yet", S["cell"]), Paragraph("—", S["cell"]), Paragraph("—", S["cell_r"]), Paragraph("—", S["cell_r"])])
    else:
        for prod, cty, pr, dm in comb:
            pr_rows.append([Paragraph(prod, S["cell"]), Paragraph(cty, S["cell"]), Paragraph(_fmt_kes(pr), S["cell_r"]), Paragraph(f"{dm:.0f} / 100" if dm else "—", S["cell_r"])])
    pt = Table(pr_rows, colWidths=[68 * mm, 34 * mm, 34 * mm, 34 * mm], repeatRows=1)
    pt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story.append(pt)
def _competitor_table(story, S, live):
    if not live["competitors"] and not live["companies"]:
        story.append(Paragraph("No competitors were tracked for this exact filter at generation time. That does not mean zero competition. It means no live Company or Competitor rows matched. Check the wider county and sector in the dashboard before concluding there is no competition.", S["body"]))
        return
    story.append(Paragraph(f"{len(live['competitors'])} competitors and {len(live['companies'])} companies were found for this filter. The table below is the live list, not a sample.", S["body"]))
    cr = [[Paragraph("Company", S["th"]), Paragraph("Sector", S["th"]), Paragraph("County", S["th"]), Paragraph("Rating", S["th_r"])]]
    for c in list(live["competitors"])[:10] + list(live["companies"])[:10]:
        cr.append([Paragraph(_clean(getattr(c, "name", ""), "Company"), S["cell"]), Paragraph(_clean(getattr(c, "sector", ""), ""), S["cell"]), Paragraph(_clean(getattr(c, "county", ""), ""), S["cell"]), Paragraph(f"{_safe_float(getattr(c, 'rating', 0)):.1f}" if _safe_float(getattr(c, "rating", 0)) else "—", S["cell_r"])])
    ct = Table(cr, colWidths=[58 * mm, 58 * mm, 28 * mm, 26 * mm], repeatRows=1)
    ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    story.append(ct)
def _charts_block(story, S, live):
    story.append(Paragraph("3.1  Pricing Evidence", S["h2"]))
    story.append(Paragraph("Live prices from KPIN and MarketMetric are shown as recorded. Prices have not been smoothed.", S["body"]))
    try:
        story.append(RLImage(_chart_price_bar(live["prices"], live["demand"]), width=170 * mm, height=75 * mm))
        story.append(Paragraph("Figure 3.1 - Average Price by Product (KES).", S["cap"]))
        story.append(Paragraph("Source: EvidLens live database at generation time (KPIN + MarketMetric). Note: Y-axis starts at zero. Values are as recorded. No demo values used.", S["note"]))
    except Exception:
        traceback.print_exc()
        story.append(Paragraph("Chart unavailable. See Table 3.1 for live prices.", S["small"]))
    story.append(Paragraph("Table 3.1 - Live Price and Demand Records", S["h3"]))
    _price_table(story, S, live)
    story.append(Paragraph("Source: EvidLens live database at generation time. Note: Table shows up to 20 records. Full records are in Annex A.", S["note"]))
    story.append(Paragraph("Pricing implication: Price at median, not at the highest observed price. Test three price points in week one and retain the one with the best volume multiplied by margin.", S["body"]))
    story.append(Paragraph("3.2  Demand Evidence", S["h2"]))
    story.append(Paragraph("Demand is the live demand score on a 0 to 100 scale. It is a snapshot of recorded demand signals, not a forecast.", S["body"]))
    try:
        dt = Table([[RLImage(_chart_demand_donut(live["demand"]), width=85 * mm, height=75 * mm)]], colWidths=[170 * mm])
        dt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        story.append(dt)
        story.append(Paragraph("Figure 3.2 - Demand Distribution.", S["cap"]))
        story.append(Paragraph("Source: MarketMetric live records. Note: High is 70 and above, Medium is 40 to 69, Low is below 40.", S["note"]))
    except Exception:
        traceback.print_exc()
    story.append(Paragraph("3.3  County Comparison", S["h2"]))
    story.append(Paragraph("County comparison helps identify arbitrage. Buy in a low-price county, sell in a high-price county, after deducting transport cost.", S["body"]))
    try:
        story.append(RLImage(_chart_county_bar(live["demand"]), width=170 * mm, height=66 * mm))
        story.append(Paragraph("Figure 3.3 - Average Price by County (KES).", S["cap"]))
        story.append(Paragraph("Source: MarketMetric live records. Note: Averages are computed from live records only. Counties with no live records are not shown.", S["note"]))
    except Exception:
        traceback.print_exc()
def _consumer_risk_block(story, S, live, plan_name, budget_str, q, sector, county):
    story.append(Paragraph("Consumer Pulse", S["h2"]))
    if not live["social"]:
        story.append(Paragraph("No live consumer mentions were found for this filter.", S["bullet"]))
    for s in live["social"][:10]:
        story.append(Paragraph(f"[{safe(getattr(s, 'platform', 'X'))}  {safe(getattr(s, 'sentiment', 'neutral'))}]  {safe(str(getattr(s, 'content', ''))[:140])}", S["bullet"]))
    story.append(Paragraph("Risk Sentinel", S["h2"]))
    if not live["news"]:
        story.append(Paragraph("No live risk alerts were found for this filter.", S["bullet"]))
    for n in live["news"][:8]:
        story.append(Paragraph(f"{safe(getattr(n, 'title', 'News'))}: {safe(str(getattr(n, 'summary', ''))[:140])}", S["bullet"]))
    story.append(Paragraph("Policy Watch", S["h2"]))
    story.append(Paragraph("Check KRA eTIMS, county permit, and sector licences before launch. If you sell food, LPG, or fuel, additional safety, KEBS, and EPRA approvals apply. Do not skip them.", S["body"]))
    if plan_name != "Enterprise":
        story.append(Paragraph("Full Regulatory Engine data is available on the Enterprise plan.", S["small"]))
    for k in live["knowledge"][:8]:
        story.append(Paragraph(f"{safe(getattr(k, 'sector', 'Policy'))}  |  {safe(str(getattr(k, 'chunk_text', ''))[:140])}", S["bullet"]))
    story.append(Paragraph("Funding Radar", S["h2"]))
    story.append(Paragraph(f"Budget provided: <b>{budget_str}</b>. For {safe(q)} in {safe(sector)} and {safe(county)}, SME funding options in order are: (1) Own savings or chama, (2) SACCO or bank with business plan and statements, (3) County, Youth, or Women Fund, (4) Supplier credit. Do not use high-interest mobile loans to cover rent. Bring this report plus six months of M-Pesa statements to the lender.", S["body"]))
    story.append(Paragraph("Export Navigator", S["h2"]))
    if plan_name != "Enterprise":
        story.append(Paragraph("Full Export Navigator data is available on the Enterprise plan.", S["small"]))
    if not live["exports"]:
        story.append(Paragraph("No live export opportunities were found for this filter. Export is a Phase 2 play. Win locally first.", S["body"]))
    for e in live["exports"][:8]:
        story.append(Paragraph(f"{safe(getattr(e, 'product', 'Product'))} to {safe(getattr(e, 'country', 'Country'))}  |  Score {safe(getattr(e, 'opportunity_score', 0))}", S["bullet"]))
def _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name="Trial"):
    story.append(Paragraph("Annex A  Full Data Tables", S["h1"]))
    story.append(Paragraph("Table A.1 below contains the full live records used for this report, up to 50 rows. It is the audit trail for Figures 3.1 to 3.3 and Table 3.1.", S["body"]))
    a_rows = [[Paragraph("Product", S["th"]), Paragraph("County", S["th"]), Paragraph("Price (KES)", S["th_r"]), Paragraph("Demand / 100", S["th_r"]), Paragraph("Sector", S["th"])]]
    all_comb = []
    for d in live["demand"][:30]:
        all_comb.append((_clean(getattr(d, "product", ""), "Product"), _clean(getattr(d, "county", ""), "Kenya"), _safe_float(getattr(d, "avg_price_kes", 0)), _safe_float(getattr(d, "demand_score", 0)), _clean(getattr(d, "sector", ""), "")))
    for p in live["prices"][:20]:
        if len(all_comb) >= 50:
            break
        all_comb.append((_clean(getattr(p, "product_name", ""), "Product"), _clean(getattr(p, "county", ""), "Kenya"), _safe_float(getattr(p, "price", 0)), 0, _clean(getattr(p, "sector", ""), "")))
    if not all_comb:
        a_rows.append([Paragraph("No live records", S["cell"]), Paragraph("—", S["cell"]), Paragraph("—", S["cell_r"]), Paragraph("—", S["cell_r"]), Paragraph("—", S["cell"])])
    else:
        for prod, cty, pr, dm, sec in all_comb:
            a_rows.append([Paragraph(prod, S["cell"]), Paragraph(cty, S["cell"]), Paragraph(_fmt_kes(pr), S["cell_r"]), Paragraph(f"{dm:.0f}" if dm else "—", S["cell_r"]), Paragraph(sec, S["cell"])])
    at = Table(a_rows, colWidths=[52 * mm, 28 * mm, 32 * mm, 28 * mm, 30 * mm], repeatRows=1)
    at.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    story.append(Paragraph("Table A.1 - Annex A - Full Live Records", S["h3"]))
    story.append(at)
    story.append(Paragraph("Source: EvidLens live database at generation time. Note: This table is the source for the charts. No rows have been added or removed except the 50-row limit.", S["note"]))
    story.append(Paragraph("Annex B  Methodology Detail and Reproducibility", S["h1"]))
    story.append(Paragraph(f"Report No: {report_no}. Generated: {now_str}. Product: {safe(q)}. Sector: {safe(sector)}. Location: {safe(location)}. Filter: County {safe(county) or 'All'}, Sub-county {safe(sub_county) or 'All'}, Ward {safe(ward) or 'All'}, Town {safe(town) or 'All'}.", S["body"]))
    story.append(Paragraph(f"Records used: PriceData {len(live['prices'])}, MarketMetric {len(live['demand'])}, Company {len(live['companies'])}, Competitor {len(live['competitors'])}, NewsArticle {len(live['news'])}, SocialMention {len(live['social'])}, KnowledgeChunk {len(live['knowledge'])}, ExportOpportunity {len(live['exports'])}.", S["body"]))
    story.append(Paragraph("Reproducibility: Re-run the same filter in the EvidLens dashboard after the next KPIN collection. Counts and prices will change as new live rows arrive. This PDF is a snapshot and is not updated automatically.", S["body"]))
    story.append(Paragraph("Quality checks: (1) No seed values were used. (2) Y-axes on charts start at zero. (3) Median is reported alongside mean. (4) Empty filters show an honest empty state.", S["body"]))
    story.append(Paragraph("References", S["h1"]))
    story.append(Paragraph("1.  EvidLens live database. KPIN daily collection, 03:00 EAT. Accessed at generation time.", S["bullet"]))
    story.append(Paragraph("2.  MarketMetric records. Demand score 0 to 100 and average price in KES.", S["bullet"]))
    story.append(Paragraph("3.  Company and Competitor records. EvidLens live database.", S["bullet"]))
    story.append(Paragraph("4.  NewsArticle and SocialMention records. Risk, policy, and consumer signals.", S["bullet"]))
    story.append(Paragraph("5.  Knowledge Base and ExportOpportunity records. Policy summaries and export routes.", S["bullet"]))
    story.append(Paragraph("6.  Kenya Revenue Authority (KRA). eTIMS and tax obligations. kra.go.ke.", S["bullet"]))
    story.append(Paragraph("7.  Central Bank of Kenya (CBK). Monetary and financial guidance. centralbank.go.ke.", S["bullet"]))
    story.append(Paragraph("8.  Energy and Petroleum Regulatory Authority (EPRA). LPG and fuel licensing. epra.go.ke.", S["bullet"]))
    story.append(Spacer(1, 6 * mm))
    sign_data = [[Paragraph("<b>Prepared by</b><br/>EvidLens Decision Intelligence<br/>app.evidlens.co.ke", S["small"]), Paragraph(f"<b>Generated</b><br/>{now_str}<br/>Plan: {safe(plan_name)}<br/>Report No: {report_no}", S["small"]), Paragraph("<b>Method</b><br/>Live DB only<br/>No demo / seed data", S["small"])]]
    sign_table = Table(sign_data, colWidths=[56 * mm, 57 * mm, 57 * mm])
    sign_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREY_BG), ("BOX", (0, 0), (-1, -1), 0.6, GREY_BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    story.append(sign_table)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Disclaimer: This report is for information only and is not investment, legal, or tax advice. Prices and demand change daily. Verify all figures on the ground before committing capital. 2026 EvidLens. All rights reserved.", S["note"]))
def _common_context(q, sector, county, location):
    now = datetime.now(UTC)
    now_str = now.strftime("%d %b %Y %H:%M EAT")
    report_no = f"EVL-{now.strftime('%Y%m%d')}-{abs(hash(safe(q) + safe(county or ''))) % 9000 + 1000}"
    return now, now_str, report_no
def _budget_parse(budget):
    budget_val = 0.0
    budget_str = "Not specified"
    if budget:
        try:
            budget_val = float(str(budget).replace(",", "").replace("KES", "").strip())
            budget_str = _fmt_kes(budget_val)
        except Exception:
            budget_str = str(budget)
    return budget_val, budget_str
def _ai_text(q, sector, county):
    ai_text = ""
    try:
        if ai_service is not None and hasattr(ai_service, "generate_insight"):
            ai_text = str(ai_service.generate_insight(q, sector, county) or "")
    except Exception:
        ai_text = ""
    return ai_text
def _benchmark(sector):
    benchmark = {}
    try:
        with Session(engine) as _db:
            benchmark = get_sector_benchmark(_db, sector) or {}
    except Exception:
        benchmark = {}
    return benchmark
def _build_pdf(path, title, q, sector, country, county, sub_county, ward, town, budget, plan_name, location, live, mode):
    S = _styles()
    now, now_str, report_no = _common_context(q, sector, county, location)
    budget_val, budget_str = _budget_parse(budget)
    m = _metrics(live)
    verdict, vcolor, vtext, has_data = _verdict(live, m)
    ai_text = _ai_text(q, sector, county)
    benchmark = _benchmark(sector)
    story = []
    _cover(story, S, title, q, sector, location, county, country, budget_str, plan_name, now_str, report_no)
    _verdict_box(story, S, verdict, vcolor, vtext)
    story.append(Paragraph("How to read this report  —  Start with the Executive Summary, then Chapter 3 for pricing and demand evidence, then Chapter 5 for risks and the action plan. Annex A contains the full data table. Annex B documents methodology and limitations. A section that says No live data means no real KPIN row existed at generation time. It has not been filled with demo values.", S["small"]))
    story.append(Paragraph("Copyright  —  2026 EvidLens. Decision Intelligence for Kenya. All rights reserved. This report is prepared for the requesting user. It is for information only and is not investment, legal, or tax advice. Validate with KRA, CBK, and county licensing before committing capital.", ParagraphStyle("Copy", parent=S["small"], textColor=GREY_TEXT, fontName="Helvetica-Oblique")))
    story.append(PageBreak())
    if mode == "EXEC_BRIEF":
        story.append(Paragraph("Executive Summary - 1 Page Snapshot", S["h1"]))
        story.append(Paragraph(f"This brief assesses <b>{safe(q)}</b> in <b>{safe(location)}</b> for the <b>{safe(sector)}</b> sector. It is based on <b>{len(live['prices']) + len(live['demand'])} live price and metric records</b>, <b>{len(live['companies'])} companies</b>, <b>{len(live['competitors'])} competitors</b>, <b>{len(live['news'])} risk signals</b>, and <b>{len(live['social'])} consumer mentions</b>.", S["body"]))
        if not has_data:
            story.append(Paragraph("The evidence base is insufficient for a decision. No live market data was available for this exact filter. Regenerate after the next KPIN collection or broaden the county or sector filter.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("5 Key Findings", S["h1"]))
        if has_data:
            story.append(Paragraph(f"Finding 1  —  Median live price is <b>{_fmt_kes(m['median_price'])}</b>. Mean is {_fmt_kes(m['avg_price'])}, range {_fmt_kes(m['min_price'])} to {_fmt_kes(m['max_price'])}.", S["bullet"]))
            story.append(Paragraph(f"Finding 2  —  Average live demand is <b>{m['avg_demand']:.0f} out of 100</b>. Above 70 with few competitors is attractive. Below 40 is a hold signal.", S["bullet"]))
            story.append(Paragraph(f"Finding 3  —  <b>{len(live['competitors'])} competitors</b> and <b>{len(live['companies'])} companies</b> tracked.", S["bullet"]))
            story.append(Paragraph(f"Finding 4  —  Budget provided is <b>{budget_str}</b>. Keep at least 30 percent for rent, transport, licences, and buffer.", S["bullet"]))
            story.append(Paragraph(f"Finding 5  —  Consumer pulse: <b>{len(live['social'])} mentions</b>. Risk sentinel: <b>{len(live['news'])} alerts</b>. Validate on the ground.", S["bullet"]))
        else:
            story.append(Paragraph("Finding 1  —  No live findings yet. Do not base a decision on this report alone.", S["bullet"]))
        story.append(Paragraph("Strategic Implications", S["h1"]))
        story.append(Paragraph(f"Implication 1  —  <b>{verdict}</b>. {vtext}", S["body"]))
        story.append(Paragraph("Implication 2  —  Price at median, not at the highest observed price. Test three price points in week one.", S["body"]))
        story.append(Paragraph("Implication 3  —  Do not compete on price alone. Compete on availability, packaging size, delivery, and trust.", S["body"]))
        story.append(Paragraph("Recommended Actions", S["h1"]))
        story.append(Paragraph("90-Day Actions", S["h2"]))
        story.append(Paragraph("Week 1-2  —  Validate. Interview 20 potential customers. Ask what they buy now, at what price, and what they dislike.", S["bullet"]))
        story.append(Paragraph("Week 3-6  —  Test. Sell a small batch at median price. Track daily volume, margin, and repeat buyers.", S["bullet"]))
        story.append(Paragraph("Week 7-12  —  Fix one variable only: price, location, or packaging. Then decide to scale or pivot.", S["bullet"]))
        story.append(Paragraph("6-12 Month Actions", S["h2"]))
        story.append(Paragraph("Month 4-6  —  If daily net profit covers rent, transport, and time, scale. Add one new product or location.", S["bullet"]))
        story.append(Paragraph("Month 7-12  —  Formalise: KRA eTIMS, county permit, M-Pesa till records. Explore SACCO or bank funding with 6 months statements.", S["bullet"]))
        story.append(Paragraph("Risks to Monitor", S["h1"]))
        if not live["news"]:
            story.append(Paragraph("No live risk alerts were found for this filter.", S["bullet"]))
        for n in live["news"][:8]:
            story.append(Paragraph(f"{safe(getattr(n, 'title', 'News'))}: {safe(str(getattr(n, 'summary', ''))[:140])}", S["bullet"]))
        story.append(Paragraph("Sources: EvidLens live database at generation time. KPIN daily collection 03:00 EAT. No demo data used.", S["note"]))
        if ai_text:
            story.append(Paragraph(f"AI insight: {safe(ai_text[:500])}", S["body"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "CONSUMER_ANALYSIS":
        story.append(Paragraph("Executive Summary", S["h1"]))
        story.append(Paragraph(f"This report assesses consumer demand for <b>{safe(q)}</b> in <b>{safe(location)}</b>. It is based on <b>{len(live['social'])} live consumer mentions</b>, <b>{len(live['demand'])} demand records</b>, and <b>{len(live['prices'])} price records</b>.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("1  Consumer Segmentation", S["h1"]))
        pos = sum(1 for s in live["social"] if "positive" in str(getattr(s, "sentiment", "")).lower() or "pos" in str(getattr(s, "sentiment", "")).lower())
        neg = sum(1 for s in live["social"] if "negative" in str(getattr(s, "sentiment", "")).lower() or "neg" in str(getattr(s, "sentiment", "")).lower())
        neu = len(live["social"]) - pos - neg
        seg_rows = [[Paragraph("Segment", S["th"]), Paragraph("Signal", S["th"]), Paragraph("Count", S["th_r"])]]
        seg_rows.append([Paragraph("Positive sentiment", S["cell"]), Paragraph("Likely buyers / advocates", S["cell"]), Paragraph(str(pos), S["cell_r"])])
        seg_rows.append([Paragraph("Neutral sentiment", S["cell"]), Paragraph("Need education / trial", S["cell"]), Paragraph(str(max(neu, 0)), S["cell_r"])])
        seg_rows.append([Paragraph("Negative sentiment", S["cell"]), Paragraph("Pain points / churn risk", S["cell"]), Paragraph(str(neg), S["cell_r"])])
        seg_rows.append([Paragraph("High demand (70+)", S["cell"]), Paragraph("Strong pull", S["cell"]), Paragraph(str(sum(1 for d in live["demand"] if _safe_float(getattr(d, "demand_score", 0)) >= 70)), S["cell_r"])])
        seg_rows.append([Paragraph("Medium demand (40-69)", S["cell"]), Paragraph("Conditional pull", S["cell"]), Paragraph(str(sum(1 for d in live["demand"] if 40 <= _safe_float(getattr(d, "demand_score", 0)) < 70)), S["cell_r"])])
        seg_rows.append([Paragraph("Low demand (<40)", S["cell"]), Paragraph("Weak pull", S["cell"]), Paragraph(str(sum(1 for d in live["demand"] if _safe_float(getattr(d, "demand_score", 0)) < 40)), S["cell_r"])])
        st = Table(seg_rows, colWidths=[58 * mm, 68 * mm, 44 * mm], repeatRows=1)
        st.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
        story.append(st)
        story.append(Paragraph("Source: SocialMention + MarketMetric live records. Segments are inferred from sentiment and demand score. No demographic data is invented.", S["note"]))
        story.append(Paragraph("2  Persona Cards", S["h1"]))
        story.append(Paragraph("Persona 1  —  Price-Sensitive Regular. Buys weekly, compares price first, loyal if price is stable and quality is consistent. Serve with small pack sizes and M-Pesa till.", S["body"]))
        story.append(Paragraph("Persona 2  —  Quality-First Buyer. Pays more for consistent quality, packaging, and receipts. Serve with branded pack, expiry date, and delivery.", S["body"]))
        story.append(Paragraph("Persona 3  —  Convenience Buyer. Buys when available near home or work. Serve with location near foot traffic and extended hours.", S["body"]))
        story.append(Paragraph("Validate personas with 20 interviews before using them for targeting. These are hypotheses from live signals, not surveyed personas.", S["note"]))
        story.append(Paragraph("3  Customer Journey Map", S["h1"]))
        j_rows = [[Paragraph("Stage", S["th"]), Paragraph("What customer does", S["th"]), Paragraph("Friction", S["th"]), Paragraph("Fix", S["th"])]]
        j_rows.append([Paragraph("Awareness", S["cell"]), Paragraph("Hears from neighbour / market", S["cell"]), Paragraph("No signage", S["cell"]), Paragraph("Clear price board", S["cell"])])
        j_rows.append([Paragraph("Consideration", S["cell"]), Paragraph("Compares price + quality", S["cell"]), Paragraph("No samples", S["cell"]), Paragraph("Small trial pack", S["cell"])])
        j_rows.append([Paragraph("Purchase", S["cell"]), Paragraph("Pays cash / M-Pesa", S["cell"]), Paragraph("No till / receipt", S["cell"]), Paragraph("M-Pesa till + receipt", S["cell"])])
        j_rows.append([Paragraph("Use", S["cell"]), Paragraph("Uses product at home", S["cell"]), Paragraph("Quality varies", S["cell"]), Paragraph("Consistent supplier", S["cell"])])
        j_rows.append([Paragraph("Repeat / Refer", S["cell"]), Paragraph("Returns if satisfied", S["cell"]), Paragraph("No follow-up", S["cell"]), Paragraph("WhatsApp list + loyalty", S["cell"])])
        jt = Table(j_rows, colWidths=[28 * mm, 48 * mm, 42 * mm, 52 * mm], repeatRows=1)
        jt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_BG]), ("GRID", (0, 0), (-1, -1), 0.4, GREY_BORDER), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
        story.append(jt)
        story.append(Paragraph("4  Consumer Pulse - Live Mentions", S["h1"]))
        if not live["social"]:
            story.append(Paragraph("No live consumer mentions were found for this filter.", S["bullet"]))
        for s in live["social"][:15]:
            story.append(Paragraph(f"[{safe(getattr(s, 'platform', 'X'))}  {safe(getattr(s, 'sentiment', 'neutral'))}]  {safe(str(getattr(s, 'content', ''))[:160])}", S["bullet"]))
        story.append(Paragraph("5  Pricing Sensitivity", S["h1"]))
        story.append(Paragraph(f"Median price is <b>{_fmt_kes(m['median_price'])}</b>, mean is {_fmt_kes(m['avg_price'])}. Price at median for trial. If repeat is below 20 percent, price, quality, or location is wrong.", S["body"]))
        _charts_block(story, S, live)
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "INDUSTRY_OUTLOOK":
        story.append(Paragraph("Executive Summary", S["h1"]))
        story.append(Paragraph(f"This Industry Outlook assesses <b>{safe(sector)}</b> in <b>{safe(location)}</b> with focus product <b>{safe(q)}</b>. It is based on <b>{len(live['prices']) + len(live['demand'])} live price and metric records</b>, <b>{len(live['companies'])} companies</b>, <b>{len(live['competitors'])} competitors</b>.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("1  Introduction", S["h1"]))
        story.append(Paragraph(f"The question addressed is whether <b>{safe(q)}</b> is feasible in <b>{safe(location)}</b> at budget <b>{budget_str}</b>. Chapter 2 documents method. Chapter 3 presents pricing and demand. Chapter 4 presents competitive and location. Chapter 5 presents consumer, risk, policy, funding, and export.", S["body"]))
        story.append(Paragraph("2  Methodology, Data Sources and Limitations", S["h1"]))
        story.append(Paragraph("Source 1  —  KPIN daily collection at 03:00 EAT. Live price records.", S["bullet"]))
        story.append(Paragraph("Source 2  —  MarketMetric records. Demand score 0 to 100 and average price in KES.", S["bullet"]))
        story.append(Paragraph("Source 3  —  Company and Competitor records.", S["bullet"]))
        story.append(Paragraph("Source 4  —  NewsArticle and SocialMention records.", S["bullet"]))
        story.append(Paragraph("Source 5  —  Knowledge Base and ExportOpportunity records.", S["bullet"]))
        story.append(Paragraph("Median is the middle value when live prices are sorted. Mean is the arithmetic average. No smoothing, no interpolation, no demo fallback. Counts are real counts at generation time.", S["body"]))
        if benchmark:
            story.append(Paragraph(f"Sector benchmark (Knowledge Base): {safe(str(benchmark)[:400])}", S["small"]))
        if ai_text:
            story.append(Paragraph(f"AI insight: {safe(ai_text[:500])}", S["small"]))
        story.append(Paragraph("3  Macro Context", S["h1"]))
        story.append(Paragraph("Kenya macro context affects demand, input costs, and credit. Check CBK monetary guidance, inflation, and FX before committing capital. This report does not forecast macro variables. It uses live micro prices as the primary evidence.", S["body"]))
        story.append(Paragraph("4  Industry Structure and Segments", S["h1"]))
        story.append(Paragraph(f"Segments in this filter: {len(live['companies'])} companies and {len(live['competitors'])} competitors tracked. Informal competitors may not be captured. Segment by price tier, pack size, and channel: market stall, kiosk, supermarket, and wholesale.", S["body"]))
        _competitor_table(story, S, live)
        story.append(Paragraph("5  Findings: Pricing, Demand and County Comparison", S["h1"]))
        _charts_block(story, S, live)
        story.append(Paragraph("6  Pricing and Margin Analysis", S["h1"]))
        story.append(Paragraph(f"At median price {_fmt_kes(m['median_price'])}, the budget {budget_str} buys roughly {int(budget_val / m['median_price']) if has_data and m['median_price'] > 0 else 0} units before other costs. This is arithmetic, not a sales forecast. Deduct transport, rent, licences, packaging, and wastage to get true margin. Test three price points in week one.", S["body"]))
        story.append(Paragraph("7  Competitive and Location Intelligence", S["h1"]))
        story.append(Paragraph(f"Focus location: <b>{safe(location)}</b>. County: {safe(county) or 'All'}. Sub-county: {safe(sub_county) or 'All'}. Ward: {safe(ward) or 'All'}. Town: {safe(town) or 'All'}. Coverage: {len(live['companies'])} companies mapped.", S["body"]))
        story.append(Paragraph("Site checklist: (1) Foot traffic at 07:00, 12:00, and 18:00 for three days. (2) Nearest competitor distance. (3) Transport cost from supplier to site. (4) Rent and goodwill against three months of revenue at median price. (5) County single business permit plus health or fire approval where applicable.", S["body"]))
        story.append(Paragraph("8  Consumer, Risk, Policy, Funding and Export", S["h1"]))
        _consumer_risk_block(story, S, live, plan_name, budget_str, q, sector, county)
        story.append(Paragraph("9  Forecasts and Scenarios", S["h1"]))
        story.append(Paragraph("Base case  —  Demand stays at current live average. Price at median. Small pilot, then scale if repeat exceeds 20 percent.", S["bullet"]))
        story.append(Paragraph("Upside case  —  Demand rises 20 percent after next KPIN collection. Competitor count stays low. Scale faster, add one location.", S["bullet"]))
        story.append(Paragraph("Downside case  —  Demand falls below 40. Price pressure from competitors. Cut stock, renegotiate supplier, or pivot product or county.", S["bullet"]))
        story.append(Paragraph("These are scenarios, not forecasts. No smoothing or projection model has been applied to live data.", S["note"]))
        story.append(Paragraph("10  Recommendations and 30-Day Action Plan", S["h1"]))
        story.append(Paragraph(f"Recommendation 1  —  <b>{verdict}</b>. {vtext}", S["bullet"]))
        story.append(Paragraph("Recommendation 2  —  Price at median and test. Keep at least 30 percent for rent, transport, licences, and one month of buffer.", S["bullet"]))
        story.append(Paragraph("Recommendation 3  —  Interview 20 potential customers before scaling.", S["bullet"]))
        if ai_text:
            story.append(Paragraph(f"AI insight: {safe(ai_text[:600])}", S["body"]))
        story.append(Paragraph("Week 1  —  Validate. Interview 20 potential customers.", S["bullet"]))
        story.append(Paragraph("Week 2  —  Test. Sell a small batch at median price. Track volume, margin, repeat.", S["bullet"]))
        story.append(Paragraph("Week 3  —  Fix. Adjust one variable only: price, location, or packaging.", S["bullet"]))
        story.append(Paragraph("Week 4  —  Decide. If daily net profit covers rent, transport, and time, scale. If not, pivot.", S["bullet"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "SECTOR_PULSE":
        story.append(Paragraph("Sector Pulse - Snapshot", S["h1"]))
        story.append(Paragraph(f"Pulse for <b>{safe(sector)}</b> in <b>{safe(location)}</b>. Focus: <b>{safe(q)}</b>. Based on <b>{len(live['prices']) + len(live['demand'])} live records</b>.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("What changed", S["h2"]))
        story.append(Paragraph(f"Median price {_fmt_kes(m['median_price'])}. Average demand {m['avg_demand']:.0f} / 100. Competitors tracked: {len(live['competitors'])}. Regenerate after next KPIN collection for fresh pulse.", S["body"]))
        _charts_block(story, S, live)
        story.append(Paragraph("Watchlist", S["h2"]))
        for n in live["news"][:5]:
            story.append(Paragraph(f"{safe(getattr(n, 'title', 'News'))}: {safe(str(getattr(n, 'summary', ''))[:140])}", S["bullet"]))
        if not live["news"]:
            story.append(Paragraph("No live risk alerts for this filter.", S["bullet"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "PRODUCT_WATCH":
        story.append(Paragraph("Product Watch", S["h1"]))
        story.append(Paragraph(f"Product: <b>{safe(q)}</b>. Sector: <b>{safe(sector)}</b>. Location: <b>{safe(location)}</b>.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("Price Watch", S["h2"]))
        _price_table(story, S, live)
        story.append(Paragraph("Competitor Watch", S["h2"]))
        _competitor_table(story, S, live)
        story.append(Paragraph("Consumer Watch", S["h2"]))
        for s in live["social"][:10]:
            story.append(Paragraph(f"[{safe(getattr(s, 'platform', 'X'))}  {safe(getattr(s, 'sentiment', 'neutral'))}]  {safe(str(getattr(s, 'content', ''))[:140])}", S["bullet"]))
        if not live["social"]:
            story.append(Paragraph("No live consumer mentions for this filter.", S["bullet"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "INVESTOR_PITCH":
        story.append(Paragraph("Investor Pitch - Summary", S["h1"]))
        story.append(Paragraph(f"Opportunity: <b>{safe(q)}</b> in <b>{safe(location)}</b>, sector <b>{safe(sector)}</b>. Ask: <b>{budget_str}</b>.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("Problem", S["h2"]))
        story.append(Paragraph("Buyers face unstable price, inconsistent quality, and poor availability. Sellers face no reliable price signal. EvidLens provides live price and demand evidence.", S["body"]))
        story.append(Paragraph("Solution", S["h2"]))
        story.append(Paragraph(f"Source at or below median {_fmt_kes(m['median_price'])}, sell at median, compete on availability, pack size, delivery, and trust. Pilot first, scale only if repeat exceeds 20 percent.", S["body"]))
        story.append(Paragraph("Market Evidence", S["h2"]))
        _charts_block(story, S, live)
        story.append(Paragraph("Competition", S["h2"]))
        _competitor_table(story, S, live)
        story.append(Paragraph("Use of Funds", S["h2"]))
        story.append(Paragraph("40 percent stock, 30 percent rent + transport + licences, 30 percent buffer and working capital. No high-interest mobile loans for rent.", S["body"]))
        story.append(Paragraph("Risks", S["h2"]))
        for n in live["news"][:5]:
            story.append(Paragraph(f"{safe(getattr(n, 'title', 'News'))}: {safe(str(getattr(n, 'summary', ''))[:140])}", S["bullet"]))
        if not live["news"]:
            story.append(Paragraph("No live risk alerts for this filter.", S["bullet"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "BUSINESS_PLAN":
        story.append(Paragraph("Business Plan - Bank Loan Pack", S["h1"]))
        story.append(Paragraph(f"Business: <b>{safe(q)}</b> in <b>{safe(location)}</b>. Sector: <b>{safe(sector)}</b>. Requested budget: <b>{budget_str}</b>.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("Business Description", S["h2"]))
        story.append(Paragraph(f"Sell {safe(q)} in {safe(location)} at median price {_fmt_kes(m['median_price'])}. Target customers in {safe(county) or 'county'} with consistent quality, receipts, and M-Pesa till.", S["body"]))
        story.append(Paragraph("Market Evidence", S["h2"]))
        _charts_block(story, S, live)
        story.append(Paragraph("Competition", S["h2"]))
        _competitor_table(story, S, live)
        story.append(Paragraph("Financial Plan", S["h2"]))
        story.append(Paragraph(f"Budget {budget_str}. At median price {_fmt_kes(m['median_price']) if has_data else 'unknown'}, budget buys roughly {int(budget_val / m['median_price']) if has_data and m['median_price'] > 0 else 0} units before other costs. This is arithmetic, not a sales forecast. Keep 30 percent buffer.", S["body"]))
        story.append(Paragraph("Licences and Compliance", S["h2"]))
        story.append(Paragraph("County single business permit, KRA eTIMS, and sector licences where applicable. Food, LPG, or fuel need KEBS and EPRA approvals.", S["body"]))
        story.append(Paragraph("Repayment Plan", S["h2"]))
        story.append(Paragraph("Repay from daily net profit after rent, transport, and stock. Bring this report plus 6 months M-Pesa statements to the lender. Do not use high-interest mobile loans to cover rent.", S["body"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    elif mode == "KRA_TAX":
        story.append(Paragraph("KRA Tax Report", S["h1"]))
        story.append(Paragraph(f"Business: <b>{safe(q)}</b> in <b>{safe(location)}</b>. Sector: <b>{safe(sector)}</b>. This is an information report, not tax advice. Confirm with KRA.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("KRA Obligations Checklist", S["h2"]))
        story.append(Paragraph("1. KRA PIN registration.", S["bullet"]))
        story.append(Paragraph("2. eTIMS invoicing for all sales.", S["bullet"]))
        story.append(Paragraph("3. Turnover tax or income tax as applicable - confirm rate with KRA.", S["bullet"]))
        story.append(Paragraph("4. VAT registration if turnover exceeds threshold - confirm with KRA.", S["bullet"]))
        story.append(Paragraph("5. PAYE if you employ staff.", S["bullet"]))
        story.append(Paragraph("6. Keep M-Pesa till + bank statements for 5 years.", S["bullet"]))
        story.append(Paragraph("Evidence Base", S["h2"]))
        story.append(Paragraph(f"Median price {_fmt_kes(m['median_price'])}, average demand {m['avg_demand']:.0f} / 100, records used: PriceData {len(live['prices'])}, MarketMetric {len(live['demand'])}.", S["body"]))
        story.append(Paragraph("Sources: kra.go.ke, KRA eTIMS guidance. Verify rates at generation time.", S["note"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    else:
        story.append(Paragraph("Executive Summary", S["h1"]))
        story.append(Paragraph(f"This report assesses the feasibility of <b>{safe(q)}</b> in <b>{safe(location)}</b> for the <b>{safe(sector)}</b> sector. It is based on <b>{len(live['prices']) + len(live['demand'])} live price and metric records</b>, <b>{len(live['companies'])} companies</b>, <b>{len(live['competitors'])} competitors</b>, <b>{len(live['news'])} risk and policy signals</b>, and <b>{len(live['social'])} consumer mentions</b> available at generation time.", S["body"]))
        if not has_data:
            story.append(Paragraph("The evidence base is insufficient for a decision. No live market data was available for this exact filter. The charts in Chapter 3 show an honest empty state. Regenerate after the next KPIN collection or broaden the county or sector filter.", S["body"]))
        _kpi_table(story, S, live, m, has_data)
        story.append(Paragraph("Key Findings", S["h2"]))
        if has_data:
            story.append(Paragraph(f"Finding 1  —  Median live price is <b>{_fmt_kes(m['median_price'])}</b>. Mean is {_fmt_kes(m['avg_price'])}, range {_fmt_kes(m['min_price'])} to {_fmt_kes(m['max_price'])}. Median is used for pricing because one outlier can distort the mean.", S["bullet"]))
            story.append(Paragraph(f"Finding 2  —  Average live demand is <b>{m['avg_demand']:.0f} out of 100</b>. Demand above 70 with few competitors is attractive. Demand below 40 is a hold signal.", S["bullet"]))
            story.append(Paragraph(f"Finding 3  —  <b>{len(live['competitors'])} competitors</b> and <b>{len(live['companies'])} companies</b> were tracked for this filter.", S["bullet"]))
            story.append(Paragraph(f"Finding 4  —  Budget provided is <b>{budget_str}</b>. If budget is below three months of operating cost at median price, start smaller or seek funding.", S["bullet"]))
        else:
            story.append(Paragraph("Finding 1  —  No live findings yet. See the empty-state note above. Do not base a decision on this report alone.", S["bullet"]))
        story.append(Paragraph("1  Introduction", S["h1"]))
        story.append(Paragraph(f"The question addressed is whether <b>{safe(q)}</b> is feasible in <b>{safe(location)}</b> at budget <b>{budget_str}</b>.", S["body"]))
        story.append(Paragraph("2  Methodology, Data Sources and Limitations", S["h1"]))
        story.append(Paragraph("Source 1  —  KPIN daily collection at 03:00 EAT. Live price records.", S["bullet"]))
        story.append(Paragraph("Source 2  —  MarketMetric records. Demand score 0 to 100 and average price in KES.", S["bullet"]))
        story.append(Paragraph("Source 3  —  Company and Competitor records.", S["bullet"]))
        story.append(Paragraph("Source 4  —  NewsArticle and SocialMention records.", S["bullet"]))
        story.append(Paragraph("Source 5  —  Knowledge Base and ExportOpportunity records.", S["bullet"]))
        story.append(Paragraph("Median is the middle value when live prices are sorted. Mean is the arithmetic average. No smoothing, no interpolation, no demo fallback. Counts are real counts at generation time.", S["body"]))
        if benchmark:
            story.append(Paragraph(f"Sector benchmark (Knowledge Base): {safe(str(benchmark)[:400])}", S["small"]))
        if ai_text:
            story.append(Paragraph(f"AI insight: {safe(ai_text[:500])}", S["small"]))
        story.append(Paragraph("3  Pricing, Demand and County Comparison", S["h1"]))
        _charts_block(story, S, live)
        story.append(Paragraph("4  Competitive and Location Intelligence", S["h1"]))
        story.append(Paragraph(f"Focus location: <b>{safe(location)}</b>. County: {safe(county) or 'All'}. Sub-county: {safe(sub_county) or 'All'}. Ward: {safe(ward) or 'All'}. Town: {safe(town) or 'All'}. Coverage: {len(live['companies'])} companies mapped.", S["body"]))
        _competitor_table(story, S, live)
        story.append(Paragraph("Site checklist: (1) Foot traffic at 07:00, 12:00, and 18:00 for three days. (2) Nearest competitor distance. (3) Transport cost from supplier to site. (4) Rent and goodwill against three months of revenue at median price. (5) County single business permit plus health or fire approval where applicable.", S["body"]))
        story.append(Paragraph("5  Consumer, Risk, Policy, Funding and Export", S["h1"]))
        _consumer_risk_block(story, S, live, plan_name, budget_str, q, sector, county)
        story.append(Paragraph("6  Recommendations and 30-Day Action Plan", S["h1"]))
        story.append(Paragraph(f"Recommendation 1  —  <b>{verdict}</b>. {vtext}", S["bullet"]))
        story.append(Paragraph("Recommendation 2  —  Price at median and test. Keep at least 30 percent for rent, transport, licences, and one month of buffer.", S["bullet"]))
        story.append(Paragraph("Recommendation 3  —  Interview 20 potential customers before scaling.", S["bullet"]))
        if ai_text:
            story.append(Paragraph(f"AI insight: {safe(ai_text[:600])}", S["body"]))
        story.append(Paragraph("Week 1  —  Validate. Interview 20 potential customers.", S["bullet"]))
        story.append(Paragraph("Week 2  —  Test. Sell a small batch at median price. Track volume, margin, repeat.", S["bullet"]))
        story.append(Paragraph("Week 3  —  Fix. Adjust one variable only: price, location, or packaging.", S["bullet"]))
        story.append(Paragraph("Week 4  —  Decide. If daily net profit covers rent, transport, and time, scale. If not, pivot.", S["bullet"]))
        _annex_block(story, S, live, q, sector, location, county, sub_county, ward, town, report_no, now_str, plan_name)
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm, title=title, author="EvidLens")
    doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
def _resolve_mode(report_type):
    u = str(report_type or "MARKET_FEASIBILITY").upper()
    if "EXEC" in u or "BRIEF" in u:
        return "EXEC_BRIEF"
    if "CONSUMER" in u or "INSIGHT" in u:
        return "CONSUMER_ANALYSIS"
    if "INDUSTRY" in u or "OUTLOOK" in u:
        return "INDUSTRY_OUTLOOK"
    if "SECTOR" in u or "PULSE" in u:
        return "SECTOR_PULSE"
    if "PRODUCT" in u or "WATCH" in u:
        return "PRODUCT_WATCH"
    if "INVESTOR" in u or "PITCH" in u:
        return "INVESTOR_PITCH"
    if "KRA" in u or "TAX" in u:
        return "KRA_TAX"
    if "BUSINESS" in u or "BANK" in u or "LOAN" in u:
        return "BUSINESS_PLAN"
    return "MARKET_FEASIBILITY"
def generate_report_pdf_file(report_type=None, q=None, sector=None, country="Kenya", county=None, sub_county=None, ward=None, town=None, budget=None, plan_name="Trial", **kwargs):
    if q is None and kwargs.get("query") is not None:
        q = kwargs.get("query")
    if q is None and isinstance(report_type, str) and sector is None and kwargs.get("sector") is None:
        q = report_type
        report_type = "MARKET_FEASIBILITY"
    if q is None:
        q = "general market analysis"
    if sector is None:
        sector = kwargs.get("sector") or "Agriculture"
    if country is None:
        country = "Kenya"
    mode = _resolve_mode(report_type)
    title = TITLE_MAP.get(mode, "Market Feasibility Report")
    location = town or ward or sub_county or county or country or "Kenya"
    live = fetch_all_live(sector=sector, county=county, product=q)
    path = _build_path(mode, q, county, town, ward, sub_county, country)
    _build_pdf(path, title, q, sector, country, county, sub_county, ward, town, budget, plan_name, location, live, mode)
    return save_to_storage(path)
def generate_market_report_pdf_file(q=None, sector=None, country="Kenya", county=None, sub_county=None, ward=None, town=None, budget=None, plan_name="Trial", **kwargs):
    report_type = kwargs.get("report_type") or kwargs.get("rtype") or "MARKET_FEASIBILITY"
    if isinstance(q, str) and q.upper() in TITLE_MAP:
        report_type = q
        q = kwargs.get("query") or kwargs.get("product") or "general market analysis"
    return generate_report_pdf_file(report_type, q, sector, country, county, sub_county, ward, town, budget, plan_name, **kwargs)
def generate_market_report_excel(db=None, sector=None, country="Kenya", county=None, sub_county=None, ward=None, town=None, q=None, **kwargs):
    try:
        import csv
        live = fetch_all_live(sector=sector, county=county, product=q)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["EvidLens Market Report", q or "", sector or "", county or "", country or ""])
        writer.writerow([])
        writer.writerow(["Product", "County", "Price KES", "Demand / 100", "Sector"])
        for d in live["demand"][:100]:
            writer.writerow([_clean(getattr(d, "product", ""), "Product"), _clean(getattr(d, "county", ""), "Kenya"), _safe_float(getattr(d, "avg_price_kes", 0)), _safe_float(getattr(d, "demand_score", 0)), _clean(getattr(d, "sector", ""), "")])
        for p in live["prices"][:100]:
            writer.writerow([_clean(getattr(p, "product_name", ""), "Product"), _clean(getattr(p, "county", ""), "Kenya"), _safe_float(getattr(p, "price", 0)), "", _clean(getattr(p, "sector", ""), "")])
        return output.getvalue().encode("utf-8")
    except Exception:
        traceback.print_exc()
        raise
