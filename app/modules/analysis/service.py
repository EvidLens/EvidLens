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

from app.modules.core.db import get_session
from app.modules.kenyalensiq.models import MarketMetric, NewsArticle, SocialMention
from main import DetailedAnalysisRequest, UserSubscription, _core # keep imports from main for now

router = APIRouter()

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
    # PASTE YOUR ENTIRE PDF FUNCTION HERE - ALL 200 LINES

@router.get("/analysis/trending")
def get_trending(session: Session = Depends(get_session)):
    # PASTE YOUR ENTIRE TRENDING FUNCTION HERE

@router.get("/analysis/search")
def search_insights(q: str = "", county: str = None, sector: str = None, min_demand: float = 0, session: Session = Depends(get_session)):
    # PASTE YOUR ENTIRE SEARCH FUNCTION HERE

@router.post("/api/mpesa/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    # PASTE YOUR ENTIRE MPESA CALLBACK HERE

NAVY = colors.HexColor("#0B1D3A")
TEAL = colors.HexColor("#009688")
LIGHT_TEAL = colors.HexColor("#E0F2F1")
GREEN = colors.HexColor("#10B981")
YELLOW = colors.HexColor("#F59E0B")
RED = colors.HexColor("#EF4444")

def create_chart(fig_func):...
def donut_chart(data, labels, title):...
def bar_chart(data, labels, title):...
