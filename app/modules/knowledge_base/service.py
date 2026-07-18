import os
import json
from sqlalchemy.orm import Session
from groq import Groq
from.models import SectorReport, KnowledgeChunk
from app.modules.market_engine.models import MarketMetric
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
    """Use Groq + RAG data to generate full sector report for ANY of 75 sectors"""
    # 1. Pull context from DATA LAYER - all sectors
    prices = db.query(PriceTrend).filter(PriceTrend.sector == sector).limit(20).all()
    demand = db.query(DemandSignal).filter(DemandSignal.sector == sector).limit(10).all()
    sentiment = db.query(SentimentSummary).filter(SentimentSummary.sector == sector).first()
    location = db.query(LocationMetric).filter(LocationMetric.sector == sector, LocationMetric.county == county).limit(5).all()
    products = db.query(ProductCatalog).filter(ProductCatalog.sector == sector).limit(10).all()

    context = {
        "sector": sector,
        "county": county or 'National',
        "top_products": [p.product_name for p in products],
        "price_data": [{'product': p.product_name, 'price_kes': p.price_kes, 'change': p.price_change_percent} for p in prices],
        "demand_signals": [{'type': d.signal_type, 'value': d.signal_value} for d in demand],
        "sentiment_score": sentiment.avg_sentiment_score if sentiment else None,
        "location_metrics": [{'county': l.county, 'metric': l.metric_type, 'value': l.metric_value} for l in location]
    }

    # 2. Groq generates report
    prompt = f"""
    You are EvidLens AI, Kenya's Decision Intelligence Platform for all 75 sectors.
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

    Data: {json.dumps(context)}
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
            "summary": "Generating report. Please try again in 60 seconds.",
            "key_insights": ["Insufficient data for this sector yet"],
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
        data_sources=["KNBS", "Jumia", "Reddit", "OSM", "Company Registry"],
        version="v1.0"
    )
    db.merge(report)
    db.commit()
    db.refresh(report)
    return report

def search_knowledge(db: Session, query: str, sector: str = None, county: str = None, top_k: int = 5):
    """RAG retrieval for Lens chatbot. Keyword + vector ready"""
    q = db.query(KnowledgeChunk)
    if sector:
        q = q.filter(KnowledgeChunk.sector == sector)
    if county:
        q = q.filter(KnowledgeChunk.county == county)
    q = q.filter(KnowledgeChunk.chunk_text.ilike(f"%{query}%"))
    return q.order_by(KnowledgeChunk.created_at.desc()).limit(top_k).all()

def ingest_sector_data(db: Session, sector: str):
    """Ingest ALL data types into KB chunks. Run weekly via cron"""
    count = 0

    # 1. Ingest price trends
    prices = db.query(PriceTrend).filter(PriceTrend.sector == sector).all()
    for p in prices:
        chunk = KnowledgeChunk(
            sector=sector,
            county=p.county,
            chunk_text=f"Price of {p.product_name} in {p.county} is KES {p.price_kes}. {p.price_change_percent}% change.",
            chunk_type="price",
            source="Data Layer Scraper",
            chunk_metadata={"product": p.product_name, "price": p.price_kes}
        )
        db.merge(chunk)
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
        db.merge(chunk)
        count += 1

    # 3. Ingest location metrics
    locations = db.query(LocationMetric).filter(LocationMetric.sector == sector).all()
    for l in locations:
        chunk = KnowledgeChunk(
            sector=sector,
            county=l.county,
            chunk_text=f"{sector} business density in {l.county}: {l.metric_value} businesses. Metric: {l.metric_type}",
            chunk_type="location",
            source="OSM/LocationIQ"
        )
        db.merge(chunk)
        count += 1

    db.commit()
    return count

def get_sector_benchmark(db: Session, sector: str):
    """Used by market_intel lane"""
    avg_price = db.query(func.avg(PriceTrend.price_kes)).filter(PriceTrend.sector==sector).scalar() or 0
    avg_growth = db.query(func.avg(DemandSignal.signal_value)).filter(DemandSignal.sector==sector).scalar() or 0
    return {
        "sector": sector,
        "avg_price_kes": float(avg_price),
        "avg_demand_growth": float(avg_growth)
    }
def get_county_by_name(name: str):
    return None
