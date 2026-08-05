from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker
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

# THIS IS THE FIX: Add SessionLocal for imports
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None

# Keep your old one for backward compat, add new one for FastAPI
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

# THIS IS WHAT FASTAPI EXPECTS
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import all SQLModel tables so metadata is registered
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
    
    SQLModel.metadata.create_all(bind=engine)
