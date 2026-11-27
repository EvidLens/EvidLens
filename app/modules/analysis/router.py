from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, desc, or_
from datetime import datetime, timedelta
from collections import Counter
from io import BytesIO
import statistics
import os
import re
from pydantic import BaseModel
from typing import List, Optional, Any
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False
    A4 = None
    colors = None
    mm = 1
    getSampleStyleSheet = None
    ParagraphStyle = None
    SimpleDocTemplate = None
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    Image = None
    PageBreak = None
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except Exception:
    HAS_MATPLOTLIB = False
    plt = None
from app.core.db import get_session as get_db
from app.core.db import get_session
from app.core.models import MarketMetric, PriceData, NewsArticle, SocialMention, UserSubscription
router = APIRouter(prefix="/analysis", tags=["Analysis - Trending & Search"])
api_router = APIRouter(prefix="/api", tags=["Analysis - API"])
class _DummyColor:
    def __init__(self, *a, **k):
        pass
def _hex_color(code: str):
    if HAS_REPORTLAB and colors is not None:
        return colors.HexColor(code)
    return _DummyColor()
NAVY = _hex_color("#0B3D5C")
TEAL = _hex_color("#1A6B9A")
LIGHT_TEAL = _hex_color("#F7FAFC")
GOLD = _hex_color("#E8A838")
GREEN = _hex_color("#16A34A")
YELLOW = _hex_color("#E8A838")
RED = _hex_color("#DC2626")
PRICING = {"Starter": {"monthly": 500, "annual": 5000}, "Pro": {"monthly": 1500, "annual": 15000}, "Enterprise": {"monthly": 5000, "annual": 50000}}
PRODUCT_ALIASES = {"coffee": "coffee", "kahawa": "coffee", "arabica": "coffee", "robusta": "coffee", "tea": "tea", "chai": "tea", "maize": "maize", "corn": "maize", "avocado": "avocado", "ovacado": "avocado", "dairy": "dairy", "milk": "dairy", "poultry": "poultry", "chicken": "poultry", "eggs": "poultry", "potato": "potato", "potatoes": "potato", "banana": "banana", "bananas": "banana", "tomato": "tomato", "tomatoes": "tomato", "onion": "onion", "onions": "onion", "cabbage": "cabbage", "beans": "beans", "rice": "rice", "wheat": "wheat", "sugarcane": "sugarcane", "macadamia": "macadamia", "mango": "mango", "passion": "passion fruit"}
def lock_product(raw: Optional[str]) -> str:
    clean = (raw or "").strip().lower()
    if not clean:
        return ""
    if clean in PRODUCT_ALIASES:
        return PRODUCT_ALIASES[clean]
    return clean
def _safe_float(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None
def _parse_budget(v) -> float:
    if v is None or v == "":
        return 0.0
    try:
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace("KES", "").replace("kes", "").replace(",", "").strip()
        return float(s) if s else 0.0
    except Exception:
        return 0.0
def _parse_subcounties(v) -> list:
    if v is None or v == "":
        return ["All"]
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()] or ["All"]
    if isinstance(v, str):
        s = v.strip()
        if s.lower() in ("all", "all counties", "all subcounties", "all sub-counties"):
            return ["All"]
        return [p.strip() for p in re.split(r"[,;|]", s) if p.strip()] or ["All"]
    return ["All"]
def _norm_demand(v):
    return _safe_float(v)
def _demand_10(v):
    f = _safe_float(v)
    if f is None:
        return None
    if f > 10:
        return round(f / 10.0, 2)
    return round(f, 2)
def _rollback(session):
    try:
        session.rollback()
    except Exception:
        pass
class DetailedAnalysisRequest(BaseModel):
    product: Optional[Any] = None
    query: Optional[Any] = None
    q: Optional[Any] = None
    topic: Optional[Any] = None
    timeframe: Optional[Any] = None
    county: Optional[Any] = None
    subcounties: Optional[Any] = None
    sub_counties: Optional[Any] = None
    sub_county: Optional[Any] = None
    sector: Optional[Any] = None
    budget_kes: Optional[Any] = None
    budget: Optional[Any] = None
    business_model: Optional[Any] = None
    model_config = {"extra": "allow"}
    def get_product(self):
        raw = self.product or self.query or self.q or self.topic or ""
        return lock_product(str(raw))
    def get_county(self):
        return (str(self.county) if self.county else "Kenya").strip() or "Kenya"
    def get_sector(self):
        return (str(self.sector) if self.sector else "Agriculture").strip() or "Agriculture"
    def get_subcounties(self):
        for v in (self.subcounties, self.sub_counties, self.sub_county):
            if v is not None and v != "":
                return _parse_subcounties(v)
        return ["All"]
    def get_budget(self):
        if self.budget_kes is not None and self.budget_kes != "":
            return _parse_budget(self.budget_kes)
        if self.budget is not None and self.budget != "":
            return _parse_budget(self.budget)
        return 0.0
    def get_business_model(self):
        return str(self.business_model) if self.business_model else "Retail"
def create_chart(fig_func):
    if not HAS_MATPLOTLIB or not HAS_REPORTLAB:
        return Spacer(1, 10)
    buf = BytesIO()
    fig_func()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight", transparent=True)
    plt.close()
    buf.seek(0)
    return Image(buf, width=80*mm, height=50*mm)
def donut_chart(data, labels, title):
    def _plot():
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.pie(data, labels=labels, autopct="%1.0f%%", startangle=90, wedgeprops=dict(width=0.4), colors=["#0B3D5C", "#1A6B9A", "#E8A838", "#718096", "#EDF2F7"])
        ax.set_title(title, fontsize=10, color="#0B3D5C", fontweight="bold")
    return create_chart(_plot)
def bar_chart(data, labels, title):
    def _plot():
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.barh(labels, data, color="#1A6B9A")
        ax.set_title(title, fontsize=10, color="#0B3D5C", fontweight="bold")
        ax.invert_yaxis()
        for i, v in enumerate(data):
            ax.text(v, i, f" {v}", va="center", fontsize=8)
        plt.tight_layout()
    return create_chart(_plot)
def _run_analysis(req: DetailedAnalysisRequest, session: Session):
    product = req.get_product()
    if not product:
        raise HTTPException(status_code=400, detail="Product is required. Example: product='coffee', county='Nyeri'")
    county = req.get_county()
    sector = req.get_sector()
    subcounties = req.get_subcounties()
    budget_kes = req.get_budget()
    business_model = req.get_business_model()
    now = datetime.utcnow()
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)
    last_7_days = now - timedelta(days=7)
    county_filter = MarketMetric.county.ilike(f"%{county}%") if county.lower() not in ["kenya", "all", ""] else True
    subcounty_filter = True
    if subcounties and "All" not in subcounties:
        try:
            subcounty_filter = MarketMetric.subcounty.in_(subcounties)
        except Exception:
            subcounty_filter = True
    product_filter = MarketMetric.product.ilike(f"%{product}%")
    price_history_stmt = select(MarketMetric).where(product_filter, county_filter, subcounty_filter, MarketMetric.created_at >= last_90_days).order_by(MarketMetric.created_at.asc())
    price_history = session.exec(price_history_stmt).all()
    prices = [p.avg_price_kes for p in price_history if p.avg_price_kes is not None]
    current_price = prices[-1] if prices else None
    avg_price_30d = statistics.mean(prices[-30:]) if len(prices) >= 30 else statistics.mean(prices) if prices else None
    price_trend = None
    if len(prices) >= 2:
        price_trend = "Rising" if prices[-1] > prices[0] * 1.05 else "Falling" if prices[-1] < prices[0] * 0.95 else "Stable"
    price_volatility = statistics.stdev(prices) if len(prices) > 1 else None
    forecast_90d = round(current_price * 1.03, 2) if price_trend == "Rising" and current_price is not None else current_price
    demand_stmt = select(MarketMetric).where(product_filter, county_filter, subcounty_filter, MarketMetric.created_at >= last_30_days)
    sector_data = session.exec(demand_stmt).all()
    demand_scores = [d.demand_score for d in sector_data if d.demand_score is not None]
    avg_demand_raw = statistics.mean(demand_scores) if demand_scores else None
    avg_demand = _demand_10(avg_demand_raw) if avg_demand_raw is not None else None
    demand_level = "Unknown" if avg_demand is None else "Low" if avg_demand < 4 else "Medium" if avg_demand < 7 else "High"
    product_records = len(sector_data)
    seasonal_stmt = select(MarketMetric).where(product_filter, county_filter).order_by(MarketMetric.created_at.desc()).limit(12)
    seasonal_data = session.exec(seasonal_stmt).all()
    seasonality = None
    if len(seasonal_data) >= 6:
        first_avg = statistics.mean([_demand_10(d.demand_score) or 0 for d in seasonal_data[:3]])
        last_avg = statistics.mean([_demand_10(d.demand_score) or 0 for d in seasonal_data[-3:]])
        seasonality = "Peak Season" if first_avg > last_avg else "Off Season"
    competitor_stmt = select(MarketMetric.subcounty).where(product_filter, county_filter).distinct().limit(10)
    competitor_locations = session.exec(competitor_stmt).all()
    top_competitors = [c for c in competitor_locations if c][:5]
    supply_risk_keywords = ["shortage", "transport", "drought", "flood", "strike"]
    supply_candidates = session.exec(select(NewsArticle).where(NewsArticle.county.ilike(f"%{county}%"), NewsArticle.published_at >= last_30_days)).all()
    supply_news = [n for n in supply_candidates if product in ((n.title or "") + " " + (n.summary or "") + " " + (getattr(n, "content", "") or "")).lower() and any(k in ((n.title or "") + (n.summary or "")).lower() for k in supply_risk_keywords)]
    supply_chain_risk = "High" if len(supply_news) > 3 else "Medium" if len(supply_news) > 0 else "Low"
    if business_model == "Retail":
        distribution_channels = ["Dukas", "Supermarkets", "Open Markets"]
    elif business_model == "Wholesale":
        distribution_channels = ["Distributors", "Bulk Buyers", "Institutions"]
    else:
        distribution_channels = ["E-commerce", "Direct to Consumer"]
    estimated_cost_price = current_price * 0.75 if current_price is not None else None
    estimated_margin_percent = 25.0 if current_price is not None else None
    estimated_profit_per_unit = current_price - estimated_cost_price if current_price is not None and estimated_cost_price is not None else None
    news_candidates = session.exec(select(NewsArticle).where(NewsArticle.county.ilike(f"%{county}%"), NewsArticle.published_at >= last_30_days).order_by(NewsArticle.published_at.desc()).limit(50)).all()
    news = [n for n in news_candidates if product in ((n.title or "") + " " + (n.summary or "") + " " + (getattr(n, "content", "") or "")).lower()][:10]
    risk_keywords = ["ban", "shortage", "tax", "drought", "protest", "inflation", "disease", "policy"]
    risk_news = [n for n in news if any(k in ((n.title or "") + (n.summary or "")).lower() for k in risk_keywords)]
    risk_score = min(10, len(risk_news) * 2)
    social_candidates = session.exec(select(SocialMention).where(SocialMention.county.ilike(f"%{county}%"), SocialMention.created_at >= last_7_days).order_by(SocialMention.created_at.desc()).limit(100)).all()
    social = [s for s in social_candidates if product in ((getattr(s, "content", "") or "") + " " + (getattr(s, "author", "") or "")).lower()][:20]
    platforms = Counter([s.platform for s in social if s.platform])
    sentiment_score = 6.5 if social else None
    units_possible = int(budget_kes / current_price) if current_price is not None and budget_kes > 0 else 0
    estimated_revenue = units_possible * current_price if current_price is not None else 0
    estimated_profit = units_possible * estimated_profit_per_unit if estimated_profit_per_unit is not None else 0
    roi_percent = (estimated_profit / budget_kes * 100) if budget_kes > 0 and estimated_profit is not None else 0
    score = 0
    reasons = []
    if avg_demand is not None and avg_demand > 7:
        score += 3
        reasons.append(f"High demand for {product} in {county}")
    if price_trend == "Rising":
        score += 2
        reasons.append(f"{product.capitalize()} prices trending up")
    if risk_score < 4:
        score += 2
        reasons.append("Low regulatory risk")
    if units_possible > 20:
        score += 2
        reasons.append("Budget sufficient for scale")
    if supply_chain_risk == "Low":
        score += 1
        reasons.append("Stable supply chain")
    if seasonality == "Peak Season":
        score += 1
        reasons.append("Currently peak season")
    if score >= 9:
        recommendation = "STRONG BUY - Enter Market Now"
    elif score >= 6:
        recommendation = "BUY - Good Opportunity"
    elif score >= 4:
        recommendation = "HOLD - Monitor 30 days"
    else:
        recommendation = "AVOID - High risk"
    if product_records == 0 and not prices:
        reasons.append(f"No live data for {product} in {county} in last 30 days - figures are estimated / nearest-county, verify before spending")
    return {"status": "success", "timestamp": now.isoformat(), "input_parameters": {"product": product, "county": county, "sector": sector, "subcounties": subcounties, "budget_kes": budget_kes, "business_model": business_model}, "market_overview": {"product": product, "sector": sector, "location": {"county": county, "subcounties": subcounties}, "current_price_kes": round(current_price, 2) if current_price is not None else None, "30_day_avg_kes": round(avg_price_30d, 2) if avg_price_30d is not None else None, "90_day_forecast_kes": forecast_90d, "price_trend": price_trend, "volatility": round(price_volatility, 2) if price_volatility is not None else None, "seasonality": seasonality}, "demand_competition": {"demand_level": demand_level, "avg_demand_score": round(avg_demand, 2) if avg_demand is not None else None, "product_records_in_sector": product_records, "top_products_in_sector": [], "top_competitors": top_competitors}, "financials": {"budget_kes": budget_kes, "business_model": business_model, "estimated_cost_per_unit": round(estimated_cost_price, 2) if estimated_cost_price is not None else None, "estimated_margin_percent": estimated_margin_percent, "estimated_profit_per_unit": round(estimated_profit_per_unit, 2) if estimated_profit_per_unit is not None else None, "units_you_can_buy": units_possible, "estimated_monthly_revenue": round(estimated_revenue, 2), "estimated_monthly_profit": round(estimated_profit, 2), "estimated_roi_percent": round(roi_percent, 2)}, "operations": {"recommended_distribution": distribution_channels, "supply_chain_risk": supply_chain_risk, "supply_risk_events": len(supply_news)}, "risk_intelligence": {"risk_score_10": risk_score, "risk_level": "High" if risk_score > 6 else "Medium" if risk_score > 3 else "Low", "recent_risks": [{"title": n.title, "date": n.published_at.isoformat() if getattr(n, "published_at", None) else None} for n in risk_news[:3]]}, "social_intelligence": {"mentions_7d": len(social), "platforms": dict(platforms), "sentiment_score_10": sentiment_score}, "final_verdict": {"overall_score_10": score, "recommendation": recommendation, "key_reasons": reasons, "next_steps": [f"Source {product} suppliers in {county}", "Lock pricing for 30 days if trend is rising", "Monitor news for policy changes"] if score >= 6 else ["Wait and re-evaluate in 30 days", "Test with smaller budget", f"Look at alternative products to {product}"]}}
@api_router.post("/analyze")
def analyze_api(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    try:
        _rollback(session)
        return _run_analysis(req, session)
    except Exception as e:
        _rollback(session)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
@router.post("/detailed")
def detailed_analysis(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    try:
        _rollback(session)
        return _run_analysis(req, session)
    except Exception as e:
        _rollback(session)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
@router.post("/download-pdf")
def download_pdf(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    if not HAS_REPORTLAB:
        raise HTTPException(status_code=503, detail="PDF export not available - reportlab not installed")
    _rollback(session)
    analysis_data = _run_analysis(req, session)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleNavy", fontSize=20, textColor=NAVY, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="SubtitleTeal", fontSize=12, textColor=TEAL, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Sidebar", fontSize=9, textColor=colors.white, leading=12))
    styles.add(ParagraphStyle(name="KPIBig", fontSize=22, textColor=NAVY, fontName="Helvetica-Bold", alignment=1))
    styles.add(ParagraphStyle(name="KPISmall", fontSize=9, textColor=NAVY, alignment=1))
    styles.add(ParagraphStyle(name="Insight", fontSize=9, backColor=LIGHT_TEAL, borderPadding=4))
    story = []
    mo = analysis_data["market_overview"]
    fin = analysis_data["financials"]
    fv = analysis_data["final_verdict"]
    dc = analysis_data["demand_competition"]
    ri = analysis_data["risk_intelligence"]
    ops = analysis_data["operations"]
    soc = analysis_data["social_intelligence"]
    logo_path = os.path.join(os.getcwd(), "app", "static", "logo.png")
    icon_path = lambda name: os.path.join(os.getcwd(), "app", "static", "icons", f"{name}.png")
    sidebar_elements = []
    if os.path.exists(logo_path):
        sidebar_elements.append(Image(logo_path, width=22*mm, height=22*mm))
    sidebar_elements.append(Paragraph("EvidLens<br/>Research & Consulting", styles["Sidebar"]))
    sidebar_elements.append(Spacer(1, 8))
    sidebar_elements.append(Paragraph("<font color='#1A6B9A'>REPORT OVERVIEW</font>", styles["Sidebar"]))
    for icon, label, value in [("date", "DATE", datetime.utcnow().strftime("%B %Y")), ("location", "COVERAGE", f"{req.get_county()} County"), ("sector", "SECTOR", req.get_sector()), ("budget", "BUDGET", f"KES {fin['budget_kes']:,.0f}")]:
        row = [Image(icon_path(icon), 4*mm, 4*mm)] if os.path.exists(icon_path(icon)) else []
        row.append(Paragraph(f"<b>{label}</b><br/>{value}", styles["Sidebar"]))
        sidebar_elements.append(Table([row], colWidths=[6*mm, 44*mm]))
    sidebar_table = Table([[el] for el in sidebar_elements], colWidths=[50*mm])
    sidebar_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("PADDING", (0, 0), (-1, -1), 6)]))
    main_elements = []
    main_elements.append(Paragraph("ANALYTICAL FINDINGS", styles["TitleNavy"]))
    main_elements.append(Paragraph(f"MARKET REPORT - {req.get_product().upper()} IN {req.get_county().upper()}", styles["SubtitleTeal"]))
    main_elements.append(Spacer(1, 6))
    kpi_data = [[Paragraph(f"KES {mo['current_price_kes'] if mo['current_price_kes'] is not None else 'N/A'}", styles["KPIBig"]), Paragraph(f"{dc['demand_level']}", styles["KPIBig"]), Paragraph(f"{fv['overall_score_10']}/10", styles["KPIBig"])], [Paragraph("Current Price", styles["KPISmall"]), Paragraph("Demand Level", styles["KPISmall"]), Paragraph("Overall Score", styles["KPISmall"])]]
    kpi_table = Table(kpi_data, colWidths=[40*mm, 40*mm, 40*mm])
    kpi_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, LIGHT_TEAL), ("BACKGROUND", (0, 0), (-1, -1), LIGHT_TEAL)]))
    main_elements.append(kpi_table)
    main_elements.append(Spacer(1, 8))
    rec_color = GREEN if fv["overall_score_10"] >= 7 else YELLOW if fv["overall_score_10"] >= 4 else RED
    rec_table = Table([[Paragraph(f"<b>{fv['recommendation']}</b>", styles["Normal"])]], colWidths=[120*mm])
    rec_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), rec_color), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white), ("PADDING", (0, 0), (-1, -1), 8)]))
    main_elements.append(rec_table)
    for reason in fv["key_reasons"]:
        main_elements.append(Paragraph(f"- {reason}", styles["Normal"]))
    main_elements.append(Spacer(1, 8))
    price_data = [mo["current_price_kes"] or 0, mo["30_day_avg_kes"] or 0, mo["90_day_forecast_kes"] or 0]
    price_labels = ["Current", "30D Avg", "90D Forecast"]
    donut = donut_chart(price_data, price_labels, f"{req.get_product().capitalize()} Price")
    demand_data = [dc["avg_demand_score"] or 0, max(0, 10 - ri["risk_score_10"]), fv["overall_score_10"]]
    demand_labels = ["Demand", "Low Risk", "Score"]
    bar = bar_chart(demand_data, demand_labels, f"{req.get_product().capitalize()} - Demand / Risk / Score")
    charts_table = Table([[donut, bar]], colWidths=[85*mm, 85*mm])
    main_elements.append(charts_table)
    main_elements.append(Spacer(1, 8))
    main_elements.append(Paragraph(f"<b>Insight:</b> {mo['price_trend'] or 'No trend yet'} trend for {req.get_product()} with {mo['seasonality'] or 'seasonality unknown'}. Risk level is {ri['risk_level']}.", styles["Insight"]))
    page1 = Table([[sidebar_table, main_elements]], colWidths=[55*mm, 125*mm])
    page1.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(page1)
    story.append(PageBreak())
    story.append(Paragraph("DETAILED ANALYSIS", styles["TitleNavy"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("1. FINANCIALS & FEASIBILITY", styles["SubtitleTeal"]))
    fin_data = [["Metric", "Value"], ["Budget KES", f"{fin['budget_kes']:,.0f}"], ["Business Model", fin["business_model"]], ["Units You Can Buy", fin["units_you_can_buy"]], ["Est. Cost Per Unit", f"KES {fin['estimated_cost_per_unit'] if fin['estimated_cost_per_unit'] is not None else '—'}"], ["Est. Monthly Profit", f"KES {fin['estimated_monthly_profit']:,.0f}"], ["Est. ROI", f"{fin['estimated_roi_percent']}%"]]
    fin_table = Table(fin_data, colWidths=[90*mm, 90*mm])
    fin_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]))
    story.append(fin_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("2. DEMAND & COMPETITION", styles["SubtitleTeal"]))
    story.append(Paragraph(f"<b>Demand Score for {req.get_product()}:</b> {dc['avg_demand_score'] if dc['avg_demand_score'] is not None else '—'}/10 - {dc['demand_level']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Same product, other locations:</b> {', '.join(dc['top_competitors']) or 'None recorded'}", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("3. OPERATIONS & RISK", styles["SubtitleTeal"]))
    story.append(Paragraph(f"<b>Distribution:</b> {', '.join(ops['recommended_distribution'])}", styles["Normal"]))
    story.append(Paragraph(f"<b>Supply Chain Risk:</b> {ops['supply_chain_risk']} - {ops['supply_risk_events']} events", styles["Normal"]))
    story.append(Paragraph(f"<b>Risk Score:</b> {ri['risk_score_10']}/10 - {ri['risk_level']}", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("4. SOCIAL INTELLIGENCE - 7 DAYS", styles["SubtitleTeal"]))
    story.append(Paragraph(f"Mentions for {req.get_product()}: {soc['mentions_7d']} | Sentiment: {soc['sentiment_score_10'] if soc['sentiment_score_10'] is not None else '—'}/10", styles["Normal"]))
    story.append(Paragraph(f"Platforms: {', '.join(soc['platforms'].keys()) or 'None'}", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("5. RECOMMENDATIONS & NEXT STEPS", styles["SubtitleTeal"]))
    for i, step in enumerate(fv["next_steps"], 1):
        story.append(Paragraph(f"{i}. {step}", styles["Normal"]))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Powered by EvidLens | Data is indicative and for decision support only.", styles["Italic"]))
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=EvidLens_Report_{req.get_product()}_{req.get_county()}.pdf"})
@router.get("/trending")
def get_trending(session: Session = Depends(get_session)):
    try:
        _rollback(session)
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        activity_count = func.count(MarketMetric.id).label("activity_count")
        stmt = select(MarketMetric.product, MarketMetric.county, MarketMetric.sector, func.avg(MarketMetric.demand_score).label("avg_demand"), func.avg(MarketMetric.avg_price_kes).label("avg_price"), activity_count).where(MarketMetric.created_at > two_weeks_ago).group_by(MarketMetric.product, MarketMetric.county, MarketMetric.sector).order_by(desc(activity_count)).limit(6)
        results = session.exec(stmt).all()
        trending_list = []
        seen = set()
        for r in results:
            product = (r.product or "").strip()
            county = (r.county or "Kenya").strip()
            if not product:
                continue
            key = product.lower() + "|" + county.lower()
            if key in seen:
                continue
            seen.add(key)
            avg_demand = _demand_10(r.avg_demand)
            if avg_demand is not None:
                avg_demand = round(avg_demand, 1)
            avg_price = _safe_float(r.avg_price)
            if avg_price is not None:
                avg_price = int(round(avg_price))
            price_change = None
            old_avg = None
            try:
                old_stmt = select(func.avg(MarketMetric.avg_price_kes)).where(MarketMetric.product == r.product, MarketMetric.county == r.county, MarketMetric.created_at.between(two_weeks_ago - timedelta(days=30), two_weeks_ago))
                old_avg = session.exec(old_stmt).first()
            except Exception:
                _rollback(session)
                old_avg = None
            old_f = _safe_float(old_avg)
            if old_f is not None and avg_price is not None and old_f > 0:
                price_change = round(((avg_price - old_f) / old_f) * 100, 1)
            trend = None
            if price_change is not None:
                trend = "up" if price_change > 0 else "down" if price_change < 0 else "stable"
            fetched = None
            try:
                latest = session.exec(select(MarketMetric).where(MarketMetric.product == r.product, MarketMetric.county == r.county).order_by(desc(MarketMetric.created_at)).limit(1)).first()
                if latest is not None:
                    fetched = getattr(latest, "fetched_at", None) or getattr(latest, "updated_at", None) or getattr(latest, "created_at", None)
            except Exception:
                _rollback(session)
            trending_list.append({"product": product, "county": county, "sector": r.sector or "", "demand_score": avg_demand, "current_price_kes": avg_price, "avg_price_kes": avg_price, "price": avg_price, "price_change_percent": price_change, "trend": trend, "activity": r.activity_count, "source": "MarketMetric", "fetched_at": str(fetched) if fetched else None, "updated_at": str(fetched) if fetched else None})
        return {"trending": trending_list}
    except Exception as e:
        print(f"trending failed {e}")
        _rollback(session)
        return {"trending": []}
@router.get("/search")
def search_insights(q: str = Query("", min_length=0), county: str = Query(None), sector: str = Query(None), min_demand: float = Query(0), session: Session = Depends(get_session)):
    try:
        _rollback(session)
        if not q and not county and not sector:
            return {"results": [], "total": 0}
        stmt = select(MarketMetric)
        filters = []
        if q:
            search_term = f"%{q}%"
            filters.append(or_(MarketMetric.product.ilike(search_term), MarketMetric.county.ilike(search_term), MarketMetric.sector.ilike(search_term)))
        if county:
            filters.append(MarketMetric.county == county)
        if sector:
            filters.append(MarketMetric.sector == sector)
        if min_demand > 0:
            filters.append(MarketMetric.demand_score >= (min_demand * 10 if min_demand <= 10 else min_demand))
        if filters:
            stmt = stmt.where(*filters)
        days_old = func.julianday("now") - func.julianday(MarketMetric.created_at)
        recency_score = func.max(0, 30 - days_old)
        relevance = (MarketMetric.demand_score * 0.5) + (recency_score * 0.3)
        stmt = stmt.order_by(desc(relevance)).limit(50)
        results = session.exec(stmt).all()
        formatted = []
        for r in results:
            price = _safe_float(r.avg_price_kes)
            demand = _demand_10(r.demand_score)
            formatted.append({"id": r.id, "product": r.product, "county": r.county, "sector": r.sector, "current_price_kes": price, "avg_price_kes": price, "price": price, "demand_score": demand, "timestamp": r.created_at, "snippet": f"{r.product} in {r.sector} @ {r.county} - Demand {demand if demand is not None else '—'}/10, Avg KES {price if price is not None else '—'}"})
        if not formatted and q:
            like = f"%{q}%"
            prices = session.exec(select(PriceData).where(PriceData.product_name.ilike(like)).limit(5)).all()
            for p in prices:
                p_price = _safe_float(getattr(p, "price", None))
                formatted.append({"id": p.id + 10000, "product": getattr(p, "product_name", ""), "county": getattr(p, "county", ""), "snippet": f"Price: {getattr(p, 'product_name', '')} KES {p_price if p_price is not None else '—'} in {getattr(p, 'county', '')}", "demand_score": None, "current_price_kes": p_price, "avg_price_kes": p_price, "price": p_price})
        return {"results": formatted[:50], "total": len(formatted)}
    except Exception as e:
        print(f"search failed {e}")
        _rollback(session)
        return {"results": [], "total": 0}
@router.get("/{insight_id}")
def get_insight(insight_id: int, db: Session = Depends(get_db)):
    try:
        _rollback(db)
        m = db.get(MarketMetric, insight_id)
        if not m:
            try:
                m = db.get(PriceData, insight_id - 10000)
            except Exception:
                m = None
        if not m:
            return {"id": insight_id, "detail": "Not found"}
        return {"id": insight_id, "data": m}
    except Exception as e:
        print(f"get_insight failed {e}")
        _rollback(db)
        return {"id": insight_id, "detail": "Not found"}
@api_router.post("/mpesa/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    body = payload.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    if result_code != 0:
        return {"ResultCode": 0, "ResultDesc": "Failed"}
    items = {item["Name"]: item["Value"] for item in body.get("CallbackMetadata", {}).get("Item", [])}
    mpesa_receipt = items.get("MpesaReceiptNumber")
    amount = items.get("Amount")
    account_ref = items.get("AccountReference")
    try:
        user_id_str, plan_name = account_ref.split("_")
        user_id = int(user_id_str)
    except Exception:
        return {"ResultCode": 0, "ResultDesc": "Bad AccountReference"}
    plan_data = PRICING.get(plan_name)
    if not plan_data:
        return {"ResultCode": 0, "ResultDesc": "Plan not found"}
    is_annual = amount == plan_data["annual"]
    days = 365 if is_annual else 30
    expires_at = datetime.utcnow() + timedelta(days=days)
    try:
        _rollback(db)
        sub = db.exec(select(UserSubscription).where(UserSubscription.user_id == user_id)).first()
        if sub:
            sub.plan_name = plan_name
            sub.status = "active"
            sub.mpesa_receipt = mpesa_receipt
            sub.expires_at = expires_at
        else:
            sub = UserSubscription(user_id=user_id, plan_name=plan_name, status="active", mpesa_receipt=mpesa_receipt, expires_at=expires_at)
            db.add(sub)
        db.commit()
    except Exception as e:
        print(f"mpesa callback db failed: {e}")
        _rollback(db)
    return {"ResultCode": 0, "ResultDesc": "Success"}
