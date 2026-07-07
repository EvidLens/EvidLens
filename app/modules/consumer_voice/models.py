from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from app.modules.db import Base
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

class ConsumerFeedback(Base):
    __tablename__ = "consumer_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=True, index=True)
    product_or_topic = Column(String, nullable=False, index=True)
    source = Column(Enum(Source), default=Source.reddit)
    source_url = Column(String, nullable=True)
    author = Column(String, nullable=True)
    
    content = Column(Text, nullable=False)
    sentiment = Column(Enum(Sentiment), default=Sentiment.neutral)
    sentiment_score = Column(Float, default=0.0)
    
    likes_mentioned = Column(Text, nullable=True)
    complaints_mentioned = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SentimentSummary(Base):
    __tablename__ = "sentiment_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    sector = Column(String, nullable=False, index=True)
    county = Column(String, nullable=True, index=True)
    product_or_topic = Column(String, nullable=False, index=True)
    
    total_mentions = Column(Integer, default=0)
    positive_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    avg_sentiment_score = Column(Float, default=0.0)
    
    top_likes = Column(Text, nullable=True)
    top_complaints = Column(Text, nullable=True)
    
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
