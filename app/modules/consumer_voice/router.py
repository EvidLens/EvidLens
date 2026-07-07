from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from.service import aggregate_sentiment, fetch_reddit_data
from.models import ConsumerFeedback, SentimentSummary
from app.modules.db import get_db

router = APIRouter()

class SentimentRequest(BaseModel):
    sector: str
    county: Optional[str] = None
    product_or_topic: str

class SentimentResponse(BaseModel):
    sector: str
    county: Optional[str]
    product_or_topic: str
    total_mentions: int
    positive: int
    neutral: int
    negative: int
    avg_sentiment_score: float
    top_likes: List[str]
    top_complaints: List[str]

@router.post("/analyze", response_model=SentimentResponse)
def analyze_consumer_sentiment(req: SentimentRequest, db: Session = Depends(get_db)):
    """
    Lane 2: Aggregates public opinions for a sector/product/county
    1. Fetches Reddit data
    2. Runs Groq Llama 3.1 sentiment
    3. Saves + returns summary
    """
    try:
        summary = aggregate_sentiment(db, req.sector, req.product_or_topic, req.county)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/feedback/{sector}")
def get_feedback_by_sector(
    sector: str,
    county: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """Get raw consumer feedback for dashboard"""
    query = db.query(ConsumerFeedback).filter(ConsumerFeedback.sector == sector)
    if county:
        query = query.filter(ConsumerFeedback.county == county)
    return query.order_by(ConsumerFeedback.created_at.desc()).limit(limit).all()

@router.get("/summary/{sector}/{product}")
def get_summary(sector: str, product: str, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get cached sentiment summary"""
    query = db.query(SentimentSummary).filter(
        SentimentSummary.sector == sector,
        SentimentSummary.product_or_topic == product
    )
    if county:
        query = query.filter(SentimentSummary.county == county)

    result = query.first()
    if not result:
        raise HTTPException(status_code=404, detail="No summary found. Run /analyze first")
    return result

@router.post("/refresh-reddit")
def refresh_reddit(sector: str, product: str, db: Session = Depends(get_db)):
    """Manually trigger Reddit fetch for a topic"""
    count = fetch_reddit_data(db, sector, product)
    return {"message": f"Fetched {count} new posts from Reddit"}
