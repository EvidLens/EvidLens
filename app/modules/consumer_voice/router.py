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
    sector: str = ""
    county: Optional[str] = None
    product_or_topic: Optional[str] = None
    product: Optional[str] = None
    text: Optional[str] = None
    model_config = {"extra": "allow"}

class SentimentResponse(BaseModel):
    sector: str = ""
    county: Optional[str] = None
    product_or_topic: Optional[str] = None
    sentiment: Optional[str] = None
    score: Optional[float] = None
    avg_sentiment_score: Optional[float] = None
    positive: Optional[int] = None
    negative: Optional[int] = None
    neutral: Optional[int] = None
    total: Optional[int] = None
    total_mentions: Optional[int] = None
    summary: Optional[dict] = None
    model_config = {"extra": "allow"}

_sentiment_pipeline = None
_vader = None

def _load_models():
    global _sentiment_pipeline, _vader
    if _sentiment_pipeline is not None or _vader is not None:
        return
    try:
        from transformers import pipeline
        _sentiment_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest", truncation=True)
        return
    except Exception as e:
        logger.warning(f"transformers model not available: {e}")
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _vader = SentimentIntensityAnalyzer()
    except Exception as e:
        logger.warning(f"vader not available: {e}")

def _classify_text(text):
    if not text or not str(text).strip():
        return "NEUTRAL", None
    _load_models()
    if _sentiment_pipeline is not None:
        try:
            result = _sentiment_pipeline(str(text)[:512])[0]
            label = str(result.get("label", "")).upper()
            score = float(result.get("score", 0))
            if "POSITIVE" in label:
                return "POSITIVE", round(score, 3)
            if "NEGATIVE" in label:
                return "NEGATIVE", round(-score, 3)
            return "NEUTRAL", 0.0
        except Exception as e:
            logger.warning(f"transformers classify failed: {e}")
    if _vader is not None:
        try:
            scores = _vader.polarity_scores(str(text))
            compound = float(scores.get("compound", 0))
            if compound >= 0.05:
                return "POSITIVE", round(compound, 3)
            if compound <= -0.05:
                return "NEGATIVE", round(compound, 3)
            return "NEUTRAL", round(compound, 3)
        except Exception as e:
            logger.warning(f"vader classify failed: {e}")
    return "NEUTRAL", None

def _normalize_feedback(f):
    text = getattr(f, "text", None) or getattr(f, "content", None) or getattr(f, "feedback", None) or getattr(f, "message", None) or ""
    stored = (getattr(f, "sentiment", None) or "").upper() if getattr(f, "sentiment", None) else None
    if stored in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
        sentiment = stored
        score = None
    else:
        sentiment, score = _classify_text(text)
    author = getattr(f, "author", None) or getattr(f, "username", None) or getattr(f, "source", None) or "Community Post"
    if str(author).strip().lower() in ["kenya consumer", "consumer"]:
        author = "Community Post"
    return {
        "id": getattr(f, "id", None),
        "text": text, "content": text, "feedback": text,
        "sentiment": sentiment, "sentiment_label": sentiment,
        "author": author,
        "source": getattr(f, "source", "") or "",
        "sector": getattr(f, "sector", "") or "",
        "county": getattr(f, "county", "") or "",
        "product_or_topic": getattr(f, "product_or_topic", "") or getattr(f, "product", "") or "",
        "created_at": getattr(f, "created_at", None),
        "score": score,
    }

@router.get("/", response_class=HTMLResponse)
async def voice_page(request: Request, sector: Optional[str] = Query(None), county: Optional[str] = Query(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    scored = [x["score"] for x in feedback if x["score"] is not None]
    avg_score = round(sum(scored) / len(scored), 3) if scored else None
    top_likes = [x["text"] for x in feedback if x["sentiment"] == "POSITIVE"][:3]
    top_complaints = [x["text"] for x in feedback if x["sentiment"] == "NEGATIVE"][:3]
    return templates.TemplateResponse("voice.html", {"request": request, "current_user": current_user, "user": current_user, "feedback": feedback, "posts": feedback, "items": feedback, "positive": positive, "neutral": neutral, "negative": negative, "positive_count": positive, "neutral_count": neutral, "negative_count": negative, "total_mentions": total, "total": total, "count": total, "avg_sentiment_score": avg_score, "sentiment_counts": {"positive": positive, "neutral": neutral, "negative": negative, "total": total}, "summary": {"positive": positive, "neutral": neutral, "negative": negative, "total": total, "avg_sentiment_score": avg_score}, "top_likes": top_likes, "top_complaints": top_complaints, "has_data": total > 0, "sector": sector or "", "county": county or ""})

@router.post("/analyze", response_model=SentimentResponse, dependencies=[Depends(require_module(module_number=2)), Depends(consume_credits(3))])
def analyze_consumer_sentiment(request: Request, req: SentimentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        topic = req.product_or_topic or req.product or ""
        summary = aggregate_sentiment(db, req.sector, topic, req.county)
        if isinstance(summary, dict):
            return SentimentResponse(sector=req.sector, county=req.county, product_or_topic=topic, **summary)
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
    stmt = select(ConsumerFeedback).where(ConsumerFeedback.sector == sector)
    if county:
        stmt = stmt.where(ConsumerFeedback.county == county)
    rows = db.exec(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No summary found")
    pos = len([r for r in rows if (r.sentiment or "").upper() == "POSITIVE"])
    neg = len([r for r in rows if (r.sentiment or "").upper() == "NEGATIVE"])
    neu = len([r for r in rows if (r.sentiment or "").upper() == "NEUTRAL"])
    return {"sector": sector, "product_or_topic": product, "county": county, "positive": pos, "negative": neg, "neutral": neu, "total": len(rows)}

@router.post("/refresh-reddit", dependencies=[Depends(require_module(module_number=2)), Depends(consume_credits(1))])
def refresh_reddit(request: Request, sector: str, product: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = fetch_reddit_data(db, sector, product)
    return {"message": f"Fetched {count}", "sector": sector, "product": product}
