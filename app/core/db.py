from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text
from typing import Generator
from .config import settings
import redis

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
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
    
    SQLModel.metadata.create_all(bind=engine)
    
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
