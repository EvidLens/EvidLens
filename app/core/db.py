from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text
from typing import Generator
from .config import settings
import redis
import os

# Fail fast if DATABASE_URL is missing
if not settings.DATABASE_URL or not settings.DATABASE_URL.strip():
    raise ValueError("DATABASE_URL is not set in environment variables")

DATABASE_URL = settings.DATABASE_URL.strip()

# Render provides postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine config
# For Postgres on Render, use small pool to avoid max_connections error
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False
    )
else:
    # Production Postgres
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

# Redis - optional
redis_client = None
if settings.REDIS_URL:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
    except Exception as e:
        print(f"Redis connection failed: {e} - continuing without cache")
        redis_client = None

def get_session() -> Generator[Session, None, None]:
    """For SQLModel Session dependency"""
    with Session(engine) as session:
        yield session

def get_db() -> Generator[Session, None, None]:
    """For FastAPI Depends"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize all tables. Safe to call on every startup."""
    from app.core.models import (
        Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter, User, Workspace,
        Subscription, MarketMetric, MarketSearch, SocialMention, Report, SectorReport,
        NewsArticle, Company, KenyaLensBusiness, GeoData, Sector, Funder, Policy,
        KenyaLensAlert, KenyaLensSubscription, KenyaLensMember, KenyaLensApiUsage,
        Deal, Funding
    )
    from app.modules.auth.models import UserRole
    from app.modules.payments.models import Payment, Subscription as PaymentSubscription, MpesaTransaction
    from app.modules.report_builder.models import ReportTemplate, ReportShare
    from app.modules.market_engine.models import Competitor
    from app.modules.pricing_engine.models import ProductPrice, RetailOutlet
    from app.modules.regulatory_engine.models import Regulation, ComplianceDeadline
    from app.modules.consumer_voice.models import ConsumerFeedback, SentimentSummary
    from app.modules.location_intel.models import LocationDemand, PropertyListing
    from app.modules.business_os.models import Business, TeamMember, Product, Invoice, Employee, AuditLog
    from app.modules.knowledge_base.models import KnowledgeDocument

    # Create all tables if not exist - won't crash if exists
    SQLModel.metadata.create_all(bind=engine, checkfirst=True)

    # Safe migrations for existing tables
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)

            if 'news_articles' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('news_articles')]
                if 'category' not in columns:
                    conn.execute(text("ALTER TABLE news_articles ADD COLUMN category VARCHAR"))
                    conn.commit()

            if 'price_data' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('price_data')]
                if 'tenant_id' not in columns:
                    conn.execute(text("ALTER TABLE price_data ADD COLUMN tenant_id INTEGER"))
                    conn.commit()
    except Exception as e:
        # Don't crash startup on migration check
        print(f"Migration check skipped: {e}")
