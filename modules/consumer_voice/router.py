from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select, desc # CHANGED: no more sqlalchemy.orm
from pydantic import BaseModel
from typing import List, Optional
from.service import aggregate_sentiment, fetch_reddit_data
from app.core.models import ConsumerFeedback, SentimentSummary # CHANGED: use core.models
from app.core.db import get_session as get_db # CHANGED: use core.db
from app.core.guards import require_module, consume_credits

router = APIRouter(prefix="/consumer-voice", tags=["Consumer Voice"])

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
@require_module(module_number=2)
def analyze_consumer_sentiment(request: Request, req: SentimentRequest, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    consume_credits(db, user_id, "api_credits", 3)
    try:
        summary = aggregate_sentiment(db, req.sector, req.product_or_topic, req.county)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback/{sector}")
@require_module(module_number=2)
def get_feedback_by_sector(request: Request, sector: str, county: Optional[str] = Query(None), limit: int = Query(50), db: Session = Depends(get_db)):
    # CHANGED TO SQLMODEL
    stmt = select(ConsumerFeedback).where(ConsumerFeedback.sector == sector)
    if county:
        stmt = stmt.where(ConsumerFeedback.county == county)
    stmt = stmt.order_by(desc(ConsumerFeedback.created_at)).limit(limit) # USE created_at
    results = db.exec(stmt).all()
    return results

@router.get("/summary/{sector}/{product}")
@require_module(module_number=2)
def get_summary(request: Request, sector: str, product: str, county: Optional[str] = Query(None), db: Session = Depends(get_db)):
    # CHANGED TO SQLMODEL
    stmt = select(SentimentSummary).where(SentimentSummary.sector == sector, SentimentSummary.product_or_topic == product)
    if county:
        stmt = stmt.where(SentimentSummary.county == county)
    result = db.exec(stmt).first()
    if not result:
        raise HTTPException(status_code=404, detail="No summary found")
    return result

@router.post("/refresh-reddit")
@require_module(module_number=2)
def refresh_reddit(request: Request, sector: str, product: str, db: Session = Depends(get_db)):
    user_id = request.state.user.id
    consume_credits(db, user_id, "api_credits", 1)
    count = fetch_reddit_data(db, sector, product)
    return {"message": f"Fetched {count}", "sector": sector, "product": product}
