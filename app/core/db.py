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
    from app.core.models import Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter, User, Workspace, Subscription, MarketMetric, MarketSearch, SocialMention, Report, SectorReport, NewsArticle, Company, KenyaLensBusiness, GeoData, Sector, Funder, Policy
    from app.modules.auth.models import UserRole
    from app.modules.payments.models import Payment, Subscription as PaymentSubscription, MpesaTransaction
    from app.modules.report_builder.models import ReportTemplate, ReportShare
    from app.modules.market_engine.models import Competitor
    from app.modules.competitive_engine.models import Deal, Funding
    from app.modules.pricing_engine.models import ProductPrice, RetailOutlet
    from app.modules.regulatory_engine.models import Regulation, ComplianceDeadline
    from app.modules.consumer_engine.models import BrandSentiment
    from app.modules.location_engine.models import LocationDemand, PropertyListing
    from app.modules.business_os.models import Contact, Battlecard
    from app.modules.knowledge_base.models import KnowledgeDocument
    from app.modules.kenyalensiq.models import KenyaLensAlert, KenyaLensSubscription, KenyaLensMember, KenyaLensApiUsage
    SQLModel.metadata.create_all(bind=engine)
