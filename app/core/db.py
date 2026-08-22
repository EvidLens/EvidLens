from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from .config import settings
import redis
import logging

logger = logging.getLogger(__name__)

if not settings.DATABASE_URL or not settings.DATABASE_URL.strip():
    raise ValueError("DATABASE_URL not set")

DATABASE_URL = settings.DATABASE_URL.strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

redis_client = None
if getattr(settings, "REDIS_URL", None):
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        redis_client.ping()
    except:
        redis_client = None

def get_session():
    with Session(engine) as session:
        yield session

def get_db():
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
    try:
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"DB exists, skipping: {e}")
        else:
            raise
