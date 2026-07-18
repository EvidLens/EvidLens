import os
import redis
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# WAVE 1 MODELS
from app.modules.market_engine.models import *

# WAVE 2 MODELS - ACTIVATE THIS
from app.modules.competitive_engine.models import Company, FundingDeal, TrafficSnapshot

# WAVE 3-9 MODELS - KEEP COMMENTED UNTIL FILES EXIST
# from app.modules.pricing_engine.models import *
# from app.modules.regulatory_engine.models import *

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db():
    return get_session()

def init_db():
    # Just create tables. All models are already imported at top
    Base.metadata.create_all(bind=engine)
