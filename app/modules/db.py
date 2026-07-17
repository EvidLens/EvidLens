import os
import redis
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

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
    # from app.modules.auth.models import User, UserRole
    # from app.modules.models import Sector, County, CoreProduct
    # from app.modules.payments.models import Payment, Subscription, MpesaTransaction
    # from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
    # from app.modules.competitive_engine.models import Company, Deal, Funding
    # from app.modules.pricing_engine.models import ProductPrice, RetailOutlet
    # from app.modules.regulatory_engine.models import Regulation
    # from app.modules.consumer_engine.models import SocialPost
    # from app.modules.location_engine.models import Site
    # from app.modules.business_os.models import Contact
    # from app.modules.knowledge_base.models import KnowledgeDocument
    # from app.modules.core.models import Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter
    
    Base.metadata.create_all(bind=engine)
