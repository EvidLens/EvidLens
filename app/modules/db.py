import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Fix for Render/Postgres
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine config
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import ALL models here so Base knows them. NO HARDCODING
    from app.modules.auth.models import User, UserRole
    from app.modules.models import Sector, County, CoreProduct
    from app.modules.payments.models import Payment, Subscription, MpesaTransaction
    from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
    from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric
    from app.modules.competitive_engine.models import Company, Deal, Funding
    from app.modules.pricing_engine.models import ProductPrice, RetailOutlet
    from app.modules.regulatory_engine.models import Regulation, ComplianceDeadline
    from app.modules.consumer_engine.models import SocialMention, BrandSentiment
    from app.modules.location_engine.models import LocationDemand, PropertyListing
    from app.modules.business_os.models import Contact, Battlecard
    from app.modules.knowledge_base.models import KnowledgeDocument
    from app.modules.core.models import Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter
    
    Base.metadata.create_all(bind=engine)
