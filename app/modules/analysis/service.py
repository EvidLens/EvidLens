from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select, func, desc, or_, SQLModel, Field, Column, JSON
from datetime import datetime, timedelta
from collections import Counter
import statistics
from io import BytesIO
import os

from pydantic import BaseModel, Field as PydanticField, field_validator
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
import matplotlib.pyplot as plt
from sqlalchemy import sqlfunc

from app.core.db import get_session, get_db
from app.modules.kenyalensiq.models import MarketMetric, NewsArticle, SocialMention
from main import DetailedAnalysisRequest, UserSubscription, _core

router = APIRouter()

NAVY = colors.HexColor("#0B1D3A")
TEAL = colors.HexColor("#009688")
LIGHT_TEAL = colors.HexColor("#E0F2F1")
GREEN = colors.HexColor("#10B981")
YELLOW = colors.HexColor("#F59E0B")
RED = colors.HexColor("#EF4444")

def create_chart(fig_func):
    buf = BytesIO()
    fig_func()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight', transparent=True)
    plt.close()
    buf.seek(0)
    return Image(buf, width=80*mm, height=50*mm)

def donut_chart(data, labels, title):
    def _plot():
        fig, ax = plt.subplots(figsize=(3,3))
        ax.pie(data, labels=labels, autopct='%1.0f%%', startangle=90, wedgeprops=dict(width=0.4), colors=['#009688','#26A69A','#4DB6AC','#80CBC4','#B2DFDB'])
        ax.set_title(title, fontsize=10, color="#0B1D3A", fontweight='bold')
    return create_chart(_plot)

def bar_chart(data, labels, title):
    def _plot():
        fig, ax = plt.subplots(figsize=(4,3))
        ax.barh(labels, data, color='#009688')
        ax.set_title(title, fontsize=10, color="#0B1D3A", fontweight='bold')
        ax.invert_yaxis()
        for i, v in enumerate(data): ax.text(v, i, f" {v}", va='center', fontsize=8)
        plt.tight_layout()
    return create_chart(_plot)

@router.post("/analysis/detailed")
def detailed_analysis(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    try:
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)
        last_7_days = now - timedelta(days=7)

        county_filter = MarketMetric.county.ilike(f"%{req.county}%")
        subcounty_filter = True
        if "All" not in req.subcounties:
            subcounty_filter = MarketMetric.subcounty.in_(req.subcounties)

        # ===== 1. PRICE + TREND + FORECAST =====
        price_history_stmt = select(MarketMetric).where(
            MarketMetric.product.ilike(f"%{req.product}%"),
            county_filter, subcounty_filter,
            MarketMetric.created_at >= last_90_days
        ).order_by(MarketMetric.created_at.asc())
        price_history = session.exec(price_history_stmt).all()
        prices = [p.avg_price_kes for p in price_history if p.avg_price_kes]

        current_price = prices[-1] if prices else None
        avg_price_30d = statistics.mean(prices[-30:]) if len(prices) >= 30 else statistics.mean(prices) if prices else None
        price_trend = "Stable"
        if len(prices) >= 2:
            price_trend = "Rising" if prices[-1] > prices[0] * 1.05 else "Falling" if prices[-1] < prices[0] * 0.95 else "Stable"
        price_volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        forecast_90d = round(current_price * 1.03, 2) if price_trend == "Rising" and current_price else current_price

        # ===== 2. DEMAND + SEASONALITY =====
        demand_stmt = select(MarketMetric).where(
            MarketMetric.sector.ilike(f"%{req.sector}%"),
            county_filter, subcounty_filter,
            MarketMetric.created_at >= last_30_days
        )
        sector_data = session.exec(demand_stmt).all()
        demand_scores = [d.demand_score for d in sector_data if d.demand_score]
        avg_demand = statistics.mean(demand_scores) if demand_scores else 0
        demand_level = "Low" if avg_demand < 4 else "Medium" if avg_demand < 7 else "High"
        products_in_sector = [d.product for d in sector_data if d.product]
        top_products = Counter(products_in_sector).most_common(5)

        seasonal_stmt = select(MarketMetric).where(
            MarketMetric.product.ilike(f"%{req.product}%"),
            county_filter
        ).order_by(MarketMetric.created_at.desc()).limit(12)
        seasonal_data = session.exec(seasonal_stmt).all()
        seasonality = "Peak Season" if len(seasonal_data) > 6 and statistics.mean([d.demand_score or 0 for d in seasonal_data[:3]]) > statistics.mean([d.demand_score or 0 for d in seasonal_data[-3:]]) else "Off Season"

        # ===== 3. COMPETITORS =====
        competitor_stmt = select(MarketMetric.product).where(
            MarketMetric.sector.ilike(f"%{req.sector}%"),
            county_filter
        ).distinct().limit(10)
        competitors = session.exec(competitor_stmt).all()
        top_competitors = [c for c in competitors if c and req.product.lower() not in c.lower()][:5]

        # ===== 4. SUPPLY CHAIN + DISTRIBUTION =====
        supply_risk_keywords = ["shortage", "transport", "drought", "flood", "strike"]
        supply_news = [n for n in session.exec(select(NewsArticle).where(
            NewsArticle.county.ilike(f"%{req.county}%"),
            NewsArticle.published_at >= last_30_days
        )).all() if any(k in ((n.title or "") + (n.summary or "")).lower() for k in supply_risk_keywords)]
        supply_chain_risk = "High" if len(supply_news) > 3 else "Medium" if len(supply_news) > 0 else "Low"

        distribution_channels = []
        if req.business_model == "Retail": distribution_channels = ["Dukas", "Supermarkets", "Open Markets"]
        elif req.business_model == "Wholesale": distribution_channels = ["Distributors", "Bulk Buyers", "Institutions"]
        else: distribution_channels = ["E-commerce", "Direct to Consumer"]

        # ===== 5. PROFIT MARGIN ESTIMATE =====
        estimated_cost_price = current_price * 0.75 if current_price else None
        estimated_margin_percent = 25.0
        estimated_profit_per_unit = current_price - estimated_cost_price if current_price and estimated_cost_price else None

        # ===== 6. RISK INTELLIGENCE =====
        news_stmt = select(NewsArticle).where(
            NewsArticle.category.ilike(f"%{req.sector}%"),
            NewsArticle.county.ilike(f"%{req.county}%"),
            NewsArticle.published_at >= last_30_days
        ).order_by(NewsArticle.published_at.desc()).limit(10)
        news = session.exec(news_stmt).all()
        risk_keywords = ["ban", "shortage", "tax", "drought", "protest", "inflation", "disease", "policy"]
        risk_news = [n for n in news if any(k in ((n.title or "") + (n.summary or "")).lower() for k in risk_keywords)]
        risk_score = min(10, len(risk_news) * 2)

        # ===== 7. SOCIAL BUZZ =====
        social_stmt = select(SocialMention).where(
            SocialMention.sector.ilike(f"%{req.sector}%"),
            SocialMention.county.ilike(f"%{req.county}%"),
            subcounty_filter if subcounty_filter!= True else True,
            SocialMention.created_at >= last_7_days
        ).order_by(SocialMention.created_at.desc()).limit(20)
        social = session.exec(social_stmt).all()
        platforms = Counter([s.platform for s in social if s.platform])
        sentiment_score = 6.5

        # ===== 8. BUDGET FEASIBILITY =====
        units_possible = int(req.budget_kes / current_price) if current_price and req.budget_kes > 0 else 0
        estimated_revenue = units_possible * current_price if current_price else 0
        estimated_profit = units_possible * estimated_profit_per_unit if estimated_profit_per_unit else 0
        roi_percent = (estimated_profit / req.budget_kes * 100) if req.budget_kes > 0 else 0

        # ===== 9. SCORING ENGINE =====
        score = 0
        reasons = []
        if avg_demand > 7: score += 3; reasons.append(f"High demand in {req.county}")
        if price_trend == "Rising": score += 2; reasons.append("Prices trending up")
        if risk_score < 4: score += 2; reasons.append("Low regulatory risk")
        if units_possible > 20: score += 2; reasons.append("Budget sufficient for scale")
        if supply_chain_risk == "Low": score += 1; reasons.append("Stable supply chain")
        if seasonality == "Peak Season": score += 1; reasons.append("Currently peak season")

        if score >= 9: recommendation = "STRONG BUY - Enter Market Now"
        elif score >= 6: recommendation = "BUY - Good Opportunity"
        elif score >= 4: recommendation = "HOLD - Monitor 30 days"
        else: recommendation = "AVOID - High risk"

        # ===== FINAL PAYLOAD =====
        return {
            "status": "success",
            "timestamp": now.isoformat(),
            "input_parameters": req.model_dump(),
            "market_overview": {
                "product": req.product,
                "sector": req.sector,
                "location": {"county": req.county, "subcounties": req.subcounties},
                "current_price_kes": round(current_price, 2) if current_price else None,
                "30_day_avg_kes": round(avg_price_30d, 2) if avg_price_30d else None,
                "90_day_forecast_kes": forecast_90d,
                "price_trend": price_trend,
                "volatility": round(price_volatility, 2),
                "seasonality": seasonality
            },
            "demand_competition": {
                "demand_level": demand_level,
                "avg_demand_score": round(avg_demand, 2),
                "top_products_in_sector": [{"product": p[0], "count": p[1]} for p in top_products],
                "top_competitors": top_competitors
            },
            "financials": {
                "budget_kes": req.budget_kes,
                "business_model": req.business_model,
                "estimated_cost_per_unit": round(estimated_cost_price, 2) if estimated_cost_price else None,
                "estimated_margin_percent": estimated_margin_percent,
                "estimated_profit_per_unit": round(estimated_profit_per_unit, 2) if estimated_profit_per_unit else None,
                "units_you_can_buy": units_possible,
                "estimated_monthly_revenue": round(estimated_revenue, 2),
                "estimated_monthly_profit": round(estimated_profit, 2),
                "estimated_roi_percent": round(roi_percent, 2)
            },
            "operations": {
                "recommended_distribution": distribution_channels,
                "supply_chain_risk": supply_chain_risk,
                "supply_risk_events": len(supply_news)
            },
            "risk_intelligence": {
                "risk_score_10": risk_score,
                "risk_level": "High" if risk_score > 6 else "Medium" if risk_score > 3 else "Low",
                "recent_risks": [{"title": n.title, "date": n.published_at.isoformat()} for n in risk_news[:3]]
            },
            "social_intelligence": {
                "mentions_7d": len(social),
                "platforms": dict(platforms),
                "sentiment_score_10": sentiment_score
            },
            "final_verdict": {
                "overall_score_10": score,
                "recommendation": recommendation,
                "key_reasons": reasons,
                "next_steps": [
                    f"Source suppliers in {req.county}",
                    "Lock pricing for 30 days if trend is rising",
                    "Monitor news for policy changes"
                ] if score >= 6 else [
                    "Wait and re-evaluate in 30 days",
                    "Test with smaller budget",
                    "Look at alternative products"
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/analysis/download-pdf")
def download_pdf(req: DetailedAnalysisRequest, session: Session = Depends(get_session)):
    analysis_data = detailed_analysis(req, session)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleNavy', fontSize=20, textColor=NAVY, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='SubtitleTeal', fontSize=12, textColor=TEAL, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='Sidebar', fontSize=9, textColor=colors.white, leading=12))
    styles.add(ParagraphStyle(name='KPIBig', fontSize=22, textColor=NAVY, fontName="Helvetica-Bold", alignment=1))
    styles.add(ParagraphStyle(name='KPISmall', fontSize=9, textColor=NAVY, alignment=1))
    styles.add(ParagraphStyle(name='Insight', fontSize=9, backColor=LIGHT_TEAL, borderPadding=4))
    story = []
    mo = analysis_data['market_overview']
    fin = analysis_data['financials']
    fv = analysis_data['final_verdict']
    dc = analysis_data['demand_competition']
    ri = analysis_data['risk_intelligence']
    ops = analysis_data['operations']
    soc = analysis_data['social_intelligence']
    logo_path = os.path.join(os.getcwd(), "app", "static", "logo.png")
    icon_path = lambda name: os.path.join(os.getcwd(), "app", "static", "icons", f"{name}.png")
    sidebar_elements = []
    if os.path.exists(logo_path): sidebar_elements.append(Image(logo_path, width=22*mm, height=22*mm))
    sidebar_elements.append(Paragraph("EvidLens<br/>Research & Consulting", styles['Sidebar']))
    sidebar_elements.append(Spacer(1, 8))
    sidebar_elements.append(Paragraph("<font color='#26A69A'>REPORT OVERVIEW</font>", styles['Sidebar']))
    for icon, label, value in [("date", "DATE", datetime.utcnow().strftime("%B %Y")), ("location", "COVERAGE", f"{req.county} County"), ("sector", "SECTOR", req.sector), ("budget", "BUDGET", f"KES {fin['budget_kes']:,}")]:
        row = [Image(icon_path(icon), 4*mm, 4*mm)] if os.path.exists(icon_path(icon)) else []
        row.append(Paragraph(f"<b>{label}</b><br/>{value}", styles['Sidebar']))
        sidebar_elements.append(Table([row], colWidths=[6*mm, 44*mm]))
    sidebar_table = Table([[el] for el in sidebar_elements], colWidths=[50*mm])
    sidebar_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), NAVY), ('PADDING', (0,0), (-1,-1), 6)]))
    main_elements = []
    main_elements.append(Paragraph("ANALYTICAL FINDINGS", styles['TitleNavy']))
    main_elements.append(Paragraph(f"MARKET REPORT - {req.product.upper()} IN {req.county.upper()}", styles['SubtitleTeal']))
    main_elements.append(Spacer(1, 6))
    kpi_data = [[Paragraph(f"KES {mo['current_price_kes'] or 'N/A'}", styles['KPIBig']), Paragraph(f"{dc['demand_level']}", styles['KPIBig']), Paragraph(f"{fv['overall_score_10']}/10", styles['KPIBig'])], [Paragraph("Current Price", styles['KPISmall']), Paragraph("Demand Level", styles['KPISmall']), Paragraph("Overall Score", styles['KPISmall'])]]
    kpi_table = Table(kpi_data, colWidths=[40*mm, 40*mm, 40*mm])
    kpi_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, LIGHT_TEAL), ('BACKGROUND', (0,0), (-1,-1), LIGHT_TEAL)]))
    main_elements.append(kpi_table)
    main_elements.append(Spacer(1, 8))
    rec_color = GREEN if fv['overall_score_10'] >= 7 else YELLOW if fv['overall_score_10'] >= 4 else RED
    rec_table = Table([[Paragraph(f"<b>{fv['recommendation']}</b>", styles['Normal'])]], colWidths=[120*mm])
    rec_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), rec_color), ('TEXTCOLOR', (0,0), (-1,-1), colors.white), ('PADDING', (0,0), (-1,-1), 8)]))
    main_elements.append(rec_table)
    for reason in fv['key_reasons']: main_elements.append(Paragraph(f"• {reason}", styles['Normal']))
    main_elements.append(Spacer(1, 8))
    price_data = [mo['current_price_kes'] or 0, mo['30_day_avg_kes'] or 0, mo['90_day_forecast_kes'] or 0]
    price_labels = ['Current', '30D Avg', '90D Forecast']
    donut = donut_chart(price_data, price_labels, "Price Trend")
    comp_data = [p['count'] for p in dc['top_products_in_sector'][:5]]
    comp_labels = [p['product'][:15] for p in dc['top_products_in_sector'][:5]]
    bar = bar_chart(comp_data, comp_labels, "Top Products in Sector")
    charts_table = Table([[donut, bar]], colWidths=[85*mm, 85*mm])
    main_elements.append(charts_table)
    main_elements.append(Spacer(1, 8))
    main_elements.append(Paragraph(f"<b>Insight:</b> {mo['price_trend']} trend with {mo['seasonality']}. Risk level is {ri['risk_level']}.", styles['Insight']))
    page1 = Table([[sidebar_table, main_elements]], colWidths=[55*mm, 125*mm])
    page1.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(page1)
    story.append(PageBreak())
    story.append(Paragraph("DETAILED ANALYSIS", styles['TitleNavy']))
    story.append(Spacer(1, 6))
    story.append(Paragraph("1. FINANCIALS & FEASIBILITY", styles['SubtitleTeal']))
    fin_data = [["Metric", "Value"], ["Budget KES", f"{fin['budget_kes']:,}"], ["Business Model", fin['business_model']], ["Units You Can Buy", fin['units_you_can_buy']], ["Est. Cost Per Unit", f"KES {fin['estimated_cost_per_unit']}"], ["Est. Monthly Profit", f"KES {fin['estimated_monthly_profit']:,}"], ["Est. ROI", f"{fin['estimated_roi_percent']}%"]]
    fin_table = Table(fin_data, colWidths=[90*mm, 90*mm])
    fin_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), NAVY), ('TEXTCOLOR', (0,0), (-1,0), colors.white)]))
    story.append(fin_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("2. DEMAND & COMPETITION", styles['SubtitleTeal']))
    story.append(Paragraph(f"<b>Demand Score:</b> {dc['avg_demand_score']}/10 - {dc['demand_level']}", styles['Normal']))
    story.append(Paragraph(f"<b>Top Competitors:</b> {', '.join(dc['top_competitors']) or 'None'}", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("3. OPERATIONS & RISK", styles['SubtitleTeal']))
    story.append(Paragraph(f"<b>Distribution:</b> {', '.join(ops['recommended_distribution'])}", styles['Normal']))
    story.append(Paragraph(f"<b>Supply Chain Risk:</b> {ops['supply_chain_risk']} - {ops['supply_risk_events']} events", styles['Normal']))
    story.append(Paragraph(f"<b>Risk Score:</b> {ri['risk_score_10']}/10 - {ri['risk_level']}", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("4. SOCIAL INTELLIGENCE - 7 DAYS", styles['SubtitleTeal']))
    story.append(Paragraph(f"Mentions: {soc['mentions_7d']} | Sentiment: {soc['sentiment_score_10']}/10", styles['Normal']))
    story.append(Paragraph(f"Platforms: {', '.join(soc['platforms'].keys())}", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("5. RECOMMENDATIONS & NEXT STEPS", styles['SubtitleTeal']))
    for i, step in enumerate(fv['next_steps'], 1): story.append(Paragraph(f"{i}. {step}", styles['Normal']))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Powered by EvidLens AI RAG | Data is indicative and for decision support only.", styles['Italic']))
    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=EvidLens_Report_{req.product}_{req.county}.pdf"})

@router.get("/analysis/trending")
def get_trending(session: Session = Depends(get_session)):
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    stmt = select(MarketMetric.product, MarketMetric.county, MarketMetric.sector, func.avg(MarketMetric.demand_score).label("avg_demand"), func.avg(MarketMetric.avg_price_kes).label("avg_price"), func.count(MarketMetric.id).label("activity_count")).where(MarketMetric.created_at > two_weeks_ago).group_by(MarketMetric.product, MarketMetric.county, MarketMetric.sector).order_by(desc("activity_count")).limit(6)
    results = session.exec(stmt).all()
    trending_list = []
    for r in results:
        old_stmt = select(func.avg(MarketMetric.avg_price_kes)).where(MarketMetric.product == r.product, MarketMetric.county == r.county, MarketMetric.created_at.between(two_weeks_ago - timedelta(days=30), two_weeks_ago))
        old_avg = session.exec(old_stmt).first() or r.avg_price
        price_change = 0
        if old_avg and old_avg > 0: price_change = round(((r.avg_price - old_avg) / old_avg) * 100, 1)
        trend = "up" if price_change > 0 else "down" if price_change < 0 else "stable"
        trending_list.append({"product": r.product, "county": r.county, "sector": r.sector, "demand_score": round(r.avg_demand or 0, 1), "current_price_kes": int(r.avg_price or 0), "price_change_percent": price_change, "trend": trend, "activity": r.activity_count})
    return {"trending": trending_list}

@router.get("/analysis/search")
def search_insights(q: str = "", county: str = None, sector: str = None, min_demand: float = 0, session: Session = Depends(get_session)):
    if not q and not county and not sector: return {"results": [], "total": 0}
    stmt = select(MarketMetric)
    filters = []
    if q:
        search_term = f"%{q}%"
        filters.append(or_(MarketMetric.product.ilike(search_term), MarketMetric.county.ilike(search_term), MarketMetric.sector.ilike(search_term)))
    if county: filters.append(MarketMetric.county == county)
    if sector: filters.append(MarketMetric.sector == sector)
    if min_demand > 0: filters.append(MarketMetric.demand_score >= min_demand)
    if filters: stmt = stmt.where(*filters)
    days_old = func.julianday('now') - func.julianday(MarketMetric.created_at)
    recency_score = func.max(0, 30 - days_old)
    relevance = (MarketMetric.demand_score * 0.5) + (recency_score * 0.3)
    stmt = stmt.order_by(desc(relevance)).limit(50)
    results = session.exec(stmt).all()
    formatted = []
    for r in results: formatted.append({"id": r.id, "product": r.product, "county": r.county, "sector": r.sector, "current_price_kes": r.avg_price_kes, "demand_score": r.demand_score, "timestamp": r.created_at})
    return {"results": formatted, "total": len(formatted)}

@router.post("/api/mpesa/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    body = payload.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")
    if result_code!= 0: return {"ResultCode": 0, "ResultDesc": "Failed"}
    items = {item["Name"]: item["Value"] for item in body.get("CallbackMetadata", {}).get("Item", [])}
    mpesa_receipt = items.get("MpesaReceiptNumber")
    amount = items.get("Amount")
    account_ref = items.get("AccountReference")
    try: user_id_str, plan_name = account_ref.split("_"); user_id = int(user_id_str)
    except: return {"ResultCode": 0, "ResultDesc": "Bad AccountReference"}
    plan_data = _core.PRICING.get(plan_name)
    if not plan_data: return {"ResultCode": 0, "ResultDesc": "Plan not found"}
    is_annual = amount == plan_data["annual"]
    days = 365 if is_annual else 30
    expires_at = datetime.utcnow() + timedelta(days=days)
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if sub: sub.plan_name = plan_name; sub.status = "active"; sub.mpesa_receipt = mpesa_receipt; sub.expires_at = expires_at
    else: sub = UserSubscription(user_id=user_id, plan_name=plan_name, status="active", mpesa_receipt=mpesa_receipt, expires_at=expires_at); db.add(sub)
    db.commit()
    return {"ResultCode": 0, "ResultDesc": "Success"}
