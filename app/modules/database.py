import os
import redis
from typing import Generator
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def get_db():
    return get_session()

def create_db_and_tables():
    # Import models here to register them with metadata
    from app.models import User, Notification, MarketMetric, PriceData, NewsArticle, SocialMention
    SQLModel.metadata.create_all(engine)
