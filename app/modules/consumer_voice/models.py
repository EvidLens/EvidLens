from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON, UniqueConstraint
from sqlalchemy.sql import func
import enum

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
    manual = "manual"

class ConsumerFeedback(SQLModel, table=True):
    __tablename__ = "consumer_feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(index=True)
    county: Optional[str] = Field(default=None, index=True)
    product_or_topic: str = Field(index=True)
    source: Source = Field(default=Source.reddit, sa_column=Column(enum.Enum(Source)))
    source_url: Optional[str] = Field(default=None, index=True, unique=True)
    author: Optional[str] = Field(default=None)

    content: str
    sentiment: Sentiment = Field(default=Sentiment.neutral, sa_column=Column(enum.Enum(Sentiment)))
    sentiment_score: float = Field(default=0.0)

    likes_mentioned: Optional[str] = Field(default=None)
    complaints_mentioned: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

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
    avg_sentiment_score: float = Field(default=0.0)

    top_likes: Optional[str] = Field(default=None)
    top_complaints: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
    last_updated: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (UniqueConstraint('sector', 'county', 'product_or_topic', name='uq_sector_county_topic'),)
