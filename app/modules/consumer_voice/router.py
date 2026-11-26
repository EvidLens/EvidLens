from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, desc
from pydantic import BaseModel
from typing import List, Optional
import logging

from .service import aggregate_sentiment, fetch_reddit_data
from app.core.models import ConsumerFeedback, SentimentSummary, User
from app.core.db import get_session as get_db
from app.core.guards import require_module, consume_credits, get_current_user

router = APIRouter(prefix="/voice", tags=["Consumer Voice"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("evidlens.voice")

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

def _classify_text(text):
    t = (text or "").lower()
    positive_words = ["good", "great", "excellent", "fair", "affordable", "cheap", "love", "happy", "quality", "fresh", "reliable", "best", "improved", "helpful"]
    negative_words = ["bad", "expensive", "high", "poor", "terrible", "awful", "scam", "fake", "late", "rude", "broken", "worst", "overpriced", "unfair", "shortage"]
    pos = sum(1 for w in positive_words if w in t)
    neg = sum(1 for w in negative_words if w in t)
    if pos > neg:
        return "POSITIVE"
    if neg > pos:
        return "NEGATIVE"
    return "NEUTRAL"

def _normalize_feedback(f):
    text = getattr(f, "text", None) or getattr(f, "content", None) or getattr(f, "feedback", None) or getattr(f, "message", None) or ""
    raw = getattr(f, "sentiment", None) or getattr(f, "sentiment_label", None) or ""
    raw = str(raw).strip().upper() if raw else ""
    if raw not in ["POSITIVE", "NEUTRAL", "NEGATIVE"]:
        raw = _classify_text(text)
    author = getattr(f, "author", None) or getattr(f, "username", None) or getattr(f, "source", None) or "Consumer"
    if str(author).strip().lower() in ["kenya consumer", "consumer"]:
        author = getattr(f, "source", None) or "Community Post"
        if not author or str(author).strip().lower() == "kenya consumer":
            author = "Community Post"
    return {
        "id": getattr(f, "id", None),
        "text": text,
        "content": text,
        "feedback": text,
        "sentiment": raw,
        "sentiment_label": raw,
        "author": author,
        "source": getattr(f, "source", "") or "",
        "sector": getattr(f, "sector", "") or "",
        "county": getattr(f, "county", "") or "",
        "product_or_topic": getattr(f, "product_or_topic", "") or getattr(f, "product", "") or "",
        "created_at": getattr(f, "created_at", None),
        "score": getattr(f, "sentiment_score", None),
    }

@router.get("/", response_class=HTMLResponse)
async def voice_page(
    request: Request,
    sector: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    feedback = []
    try:
        stmt = select(ConsumerFeedback).order_by(desc(ConsumerFeedback.created_at)).limit(100)
        if sector:
            stmt = stmt.where(ConsumerFeedback.sector == sector)
        if county:
            stmt = stmt.where(ConsumerFeedback.county == county)
        rows = db.exec(stmt).all()
        feedback = [_normalize_feedback(r) for r in rows]
    except Exception as e:
        logger.exception(f"voice_page failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        feedback = []

    positive = len([x for x in feedback if x["sentiment"] == "POSITIVE"])
    neutral = len([x for x in feedback if x["sentiment"] == "NEUTRAL"])
    negative = len([x for x in feedback if x["sentiment"] == "NEGATIVE"])
    total = len(feedback)

    return templates.TemplateResponse(
        "voice.html",
        {
            "request": request,
            "current_user": current_user,
            "user": current_user,
            "feedback": feedback,
            "posts": feedback,
            "items": feedback,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "positive_count": positive,
            "neutral_count": neutral,
            "negative_count": negative,
            "total_mentions": total,
            "total": total,
            "has_data": total > 0,
            "sector": sector or "",
            "county": county or "",
        }
    )

@router.post("/analyze", response_model=SentimentResponse, dependencies=[Depends(require_module(module_number=2)), Depends(consume_credits(3))])
def analyze_consumer_sentiment(request: Request, req: SentimentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        summary = aggregate_sentiment(db, req.sector, req.product_or_topic, req.county)
        return summary
    except Exception as e:
        logger.exception(f"analyze_consumer_sentiment failed: {e}")
        raise HTTPException(status_code=500, detail="Analysis failed. Please try again.")

@router.get("/feedback/{sector}", dependencies=[Depends(require_module(module_number=2))])
def get_feedback_by_sector(request: Request, sector: str, county: Optional[str] = Query(None), limit: int = Query(50), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ConsumerFeedback).where(ConsumerFeedback.sector == sector)
    if county:
        stmt = stmt.where(ConsumerFeedback.county == county)
    stmt = stmt.order_by(desc(ConsumerFeedback.created_at)).limit(limit)
    results = db.exec(stmt).all()
    return [_normalize_feedback(r) for r in results]

@router.get("/summary/{sector}/{product}", dependencies=[Depends(require_module(module_number=2))])
def get_summary(request: Request, sector: str, product: str, county: Optional[str] = Query(None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(SentimentSummary).where(SentimentSummary.sector == sector, SentimentSummary.product_or_topic == product)
    if county:
        stmt = stmt.where(SentimentSummary.county == county)
    result = db.exec(stmt).first()
    if not result:
        raise HTTPException(status_code=404, detail="No summary found")
    return result

@router.post("/refresh-reddit", dependencies=[Depends(require_module(module_number=2)), Depends(consume_credits(1))])
def refresh_reddit(request: Request, sector: str, product: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = fetch_reddit_data(db, sector, product)
    return {"message": f"Fetched {count}", "sector": sector, "product": product}
