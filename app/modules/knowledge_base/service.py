import os
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from groq import Groq
from.models import SectorReport, KnowledgeChunk, FMCGInsight, KENYA_SECTORS
from app.modules.data_layer.models import PriceTrend, DemandSignal, LocationMetric
from app.modules.consumer_voice.models import SentimentSummary

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

def get_sector_report(db: Session, sector: str, county: str = None):
    """Fetch prebuilt report. Powers dashboard auto-load"""
    query = db.query(SectorReport).filter(SectorReport.sector == sector)
    if county:
        query = query.filter(SectorReport.county == county)
    return query.order_by(SectorReport.updated_at.desc()).first()

def generate_report_with_groq(db: Session, sector: str, county: str = None):
    """Use Groq + RAG data to generate full sector report"""
    # 1. Pull context from other lanes
    prices = db.query(PriceTrend).filter(PriceTrend.sector == sector).limit(10).all()
    demand = db.query(DemandSignal).filter(DemandSignal.sector == sector).limit(5).all()
    sentiment = db.query(SentimentSummary).filter(SentimentSummary.sector == sector).first()
    location = db.query(LocationMetric).filter(LocationMetric.sector == sector).limit(5).all()

    context = f"""
    Sector: {sector}
    County: {county or 'National'}
    Price Data: {[{'product': p.product_name, 'price': p.price_kes} for p in prices]}
    Demand Signals: {[{'type': d.signal_type, 'value': d.signal_value} for d in demand]}
    Sentiment: {sentiment.avg_sentiment_score if sentiment else 'N/A'}
    Location Metrics: {[{'county': l.county, 'value': l.metric_value} for l in location]}
    """

    # 2. Groq generates report
    prompt = f"""
    You are EvidLens AI, Kenya's Decision Intelligence Platform.
    Using this data, generate a market report for {sector} in {county or 'Kenya'}.

    Return JSON only:
    {{
      "title": "string",
      "summary": "3 sentence market overview",
      "key_insights": ["insight1", "insight2", "insight3"],
      "market_size_kes": number,
      "growth_rate_percent": number,
      "top_challenges": ["challenge1", "challenge2"],
      "opportunities": ["opportunity1", "opportunity2"]
    }}

    Data: {context}
    """

    try:
        chat = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        result = json.loads(chat.choices[0].message.content)
    except Exception as e:
        result = {
            "title": f"{sector} Market Report",
            "summary": "Data unavailable",
            "key_insights": [],
            "market_size_kes": 0,
            "growth_rate_percent": 0,
            "top_challenges": [],
            "opportunities": []
        }

    # 3. Save to DB
    report = SectorReport(
        sector=sector,
        county=county,
        title=result["title"],
        summary=result["summary"],
        key_insights=result["key_insights"],
        market_size_kes=result["market_size_kes"],
        growth_rate_percent=result["growth_rate_percent"],
        top_challenges=result["top_challenges"],
        opportunities=result["opportunities"],
        data_sources=["KNBS", "Jumia", "Reddit", "OSM"],
        version="v1.0"
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

def search_knowledge(db: Session, query: str, sector: str = None, county: str = None, top_k: int = 5):
    """RAG retrieval for Lens chatbot. Simple keyword + sector filter"""
    q = db.query(KnowledgeChunk)
    if sector:
        q = q.filter(KnowledgeChunk.sector == sector)
    if county:
        q = q.filter(KnowledgeChunk.county == county)

    q = q.filter(KnowledgeChunk.chunk_text.ilike(f"%{query}%"))
    return q.limit(top_k).all()

def ingest_sector_data(db: Session, sector: str):
    """Ingest KNBS + FMCG + Price data into KB chunks. Run weekly"""
    count = 0

    # 1. Ingest price trends as chunks
    prices = db.query(PriceTrend).filter(PriceTrend.sector == sector).all()
    for p in prices:
        chunk = KnowledgeChunk(
            sector=sector,
            county=p.county,
            chunk_text=f"Price of {p.product_name} in {p.county} is KES {p.price_kes}. Change: {p.price_change_percent}%",
            chunk_type="price",
            source="Jumia/Naivas Scraper",
            metadata={"product": p.product_name, "price": p.price_kes}
        )
        db.add(chunk)
        count += 1

    # 2. Ingest demand signals
    demands = db.query(DemandSignal).filter(DemandSignal.sector == sector).all()
    for d in demands:
        chunk = KnowledgeChunk(
            sector=sector,
            county=d.county,
            chunk_text=f"Demand signal for {sector}: {d.signal_type} = {d.signal_value} in {d.period}",
            chunk_type="demand",
            source="KNBS/Google Trends"
        )
        db.add(chunk)
        count += 1

    # 3. Seed FMCG insights
    if sector == "Food & Beverage":
        insight = FMCGInsight(
            category="Food & Staples",
            subcategory="Maize flour",
            insight_text="Maize flour demand peaks in rural counties. Price arbitrage opportunity between Nairobi and Western Kenya",
            price_trend="rising",
            demand_level="high",
            county="Western"
        )
        db.merge(insight)

    db.commit()
    return count
