from sqlmodel import Session, select
from app.modules.data_layer.db import engine
import logging
import json
import os

logger = logging.getLogger(__name__)

from app.modules.report_builder.models import ReportTemplate, ReportType
from app.modules.consumer_voice.models import SentimentSummary, Sentiment
from app.modules.payments.models import SubscriptionTier, Subscription
from app.modules.location_intel.models import County

def load_kenya_sectors():
    path = os.path.join(os.path.dirname(__file__), "..", "seed_data", "kenya_sectors.json")
    path = os.path.abspath(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [s["name"] for s in data["sectors"]]

def get_counties(session):
    return session.exec(select(County.name)).all()

def seed_data():
    logger.info("Running seed data...")
    with Session(engine) as session:
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
        
        sectors = load_kenya_sectors()
        counties = get_counties(session)
        
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
        
        logger.info(f"Seeded {len(templates)} templates")
        logger.info(f"Using {len(sectors)} sectors from json and {len(counties)} counties from DB")
        
        session.commit()
        logger.info("Seed data complete")

if __name__ == "__main__":
    seed_data()
