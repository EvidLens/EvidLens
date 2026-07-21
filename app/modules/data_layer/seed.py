from sqlmodel import Session, select
from app.modules.db import engine
import logging
from datetime import datetime, timedelta
import enum

logger = logging.getLogger(__name__)

# Import your models
from app.modules.report_builder.models import ReportTemplate, ReportType
from app.modules.consumer_voice.models import SentimentSummary, Sentiment
from app.modules.payments.models import SubscriptionTier, Subscription

def seed_data():
    """Seed initial data for SME Intelligence"""
    logger.info("Running seed data...")
    with Session(engine) as session:
        
        # 1. SEED REPORT TEMPLATES
        templates = [
            ReportTemplate(
                name="Market Feasibility - Free",
                report_type=ReportType.MARKET_FEASIBILITY,
                sections=["executive_summary", "market_size", "demand", "competitors", "risks"],
                is_premium=False,
                description="Basic market feasibility for any sector in Kenya"
            ),
            ReportTemplate(
                name="Consumer Voice Analysis",
                report_type=ReportType.CONSUMER_ANALYSIS,
                sections=["sentiment_overview", "top_complaints", "top_likes", "county_breakdown"],
                is_premium=False,
                description="Reddit, Jumia, Naivas reviews sentiment"
            ),
            ReportTemplate(
                name="Business Plan + KRA",
                report_type=ReportType.BUSINESS_PLAN,
                sections=["executive_summary", "market_analysis", "financials", "kra_compliance", "risk_mitigation"],
                is_premium=True,
                description="Full business plan with KRA tax projections"
            ),
            ReportTemplate(
                name="Investor Pitch Deck",
                report_type=ReportType.INVESTOR_PITCH,
                sections=["problem", "solution", "market", "traction", "financials", "team", "ask"],
                is_premium=True,
                description="10-slide pitch deck for investors"
            ),
            ReportTemplate(
                name="Competitor Tracker",
                report_type=ReportType.COMPETITOR_TRACKER,
                sections=["competitor_list", "pricing", "gaps", "opportunities"],
                is_premium=False,
                description="Track competitors in your sector"
            ),
        ]
        
        for template in templates:
            existing = session.exec(select(ReportTemplate).where(ReportTemplate.name == template.name)).first()
            if not existing:
                session.add(template)
        
        # 2. SEED SENTIMENT SUMMARY FOR TOP SECTORS
        sectors = ["retail", "agriculture", "matatu", "salon", "restaurant"]
        counties = ["Nairobi", "Kiambu", "Mombasa", "Kisumu"]
        
        for sector in sectors:
            for county in counties:
                existing = session.exec(
                    select(SentimentSummary).where(
                        SentimentSummary.sector == sector, 
                        SentimentSummary.county == county
                    )
                ).first()
                if not existing:
                    summary = SentimentSummary(
                        sector=sector,
                        county=county,
                        product_or_topic="general",
                        total_mentions=0,
                        positive_count=0,
                        neutral_count=0,
                        negative_count=0,
                        avg_sentiment_score=0.0,
                        top_likes="",
                        top_complaints=""
                    )
                    session.add(summary)
        
        # 3. SEED DEFAULT SUBSCRIPTION TIERS INFO
        # This is just for reference - actual subscriptions are created per user
        logger.info(f"Seeded {len(templates)} templates and base sentiment tables")
        
        session.commit()
        logger.info("Seed data complete ✅")

if __name__ == "__main__":
    seed_data()
