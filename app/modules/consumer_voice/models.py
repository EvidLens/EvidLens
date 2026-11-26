from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum
import enum

def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

class Source(str, enum.Enum):
    reddit = "reddit"
    jumia = "jumia"
    naivas = "naivas"
    google = "google"
    twitter = "twitter"
    x = "x"
    tiktok = "tiktok"
    facebook = "facebook"
    manual = "manual"

class ConsumerVoiceFeedback(SQLModel, table=True):
    __tablename__ = "consumer_voice_feedback"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True)
    county: Optional[str] = Field(default=None, index=True)
    product_or_topic: str = Field(index=True)
    source: Optional[Source] = Field(default=None, sa_column=Column(SQLEnum(Source)))
    source_url: Optional[str] = Field(default=None, index=True, unique=True)
    author: Optional[str] = Field(default=None)
    content: str = Field(default="")
    sentiment: Optional[Sentiment] = Field(default=None, sa_column=Column(SQLEnum(Sentiment)))
    sentiment_score: Optional[float] = Field(default=None)
    likes_mentioned: Optional[str] = Field(default=None)
    complaints_mentioned: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})

ConsumerFeedback = ConsumerVoiceFeedback

class SentimentSummary(SQLModel, table=True):
    __tablename__ = "sentiment_summary"
    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True)
    county: Optional[str] = Field(default=None, index=True)
    product_or_topic: str = Field(index=True)
    total_mentions: int = Field(default=0)
    positive_count: int = Field(default=0)
    neutral_count: int = Field(default=0)
    negative_count: int = Field(default=0)
    avg_sentiment_score: Optional[float] = Field(default=None)
    top_likes: Optional[str] = Field(default=None)
    top_complaints: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now()})
    last_updated: datetime = Field(default_factory=_utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})
