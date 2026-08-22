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
    # CORE MODELS - ALL TABLES
    from app.core.models import (
        Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter, User, Workspace,
        Subscription, MarketMetric, MarketSearch, SocialMention, Report, SectorReport,
        NewsArticle, Company, KenyaLensBusiness, GeoData, Sector, Funder, Policy,
        KenyaLensAlert, KenyaLensSubscription, KenyaLensMember, KenyaLensApiUsage,
        Deal, Funding, PriceData, KnowledgeChunk, ExportOpportunity,
        Payment, KenyaLensBusiness, KenyaLensSurvey, KenyaLensResponse, KenyaTenant,
        KenyaLensMember, KenyaLensAlert, KenyaLensApiUsage, Notification,
        ConsumerFeedback, SentimentSummary, DataSource, Competitor, KenyaLensSubscription,
        MarketSearch, SocialMention, KenyaLensApiUsage
    )
    from app.modules.auth.models import AuthUser
    try:
        from app.modules.auth.models import UserRole
    except:
        pass
    try:
        from app.modules.payments.models import Payment as PaymentModel, Subscription as PaymentSubscription, MpesaTransaction
    except:
        pass
    try:
        from app.modules.report_builder.models import ReportTemplate, ReportShare
    except:
        pass
    try:
        from app.modules.market_engine.models import Competitor as MarketCompetitor
    except:
        pass
    try:
        from app.modules.pricing_engine.models import ProductPrice, RetailOutlet
    except:
        pass
    try:
        from app.modules.regulatory_engine.models import Regulation, ComplianceDeadline
    except:
        pass
    try:
        from app.modules.consumer_voice.models import ConsumerFeedback as CVFeedback, SentimentSummary as CVSummary
    except:
        pass
    try:
        from app.modules.location_intel.models import LocationDemand, PropertyListing
    except:
        pass
    try:
        from app.modules.business_os.models import Business, TeamMember, Product, Invoice, Employee, AuditLog
    except:
        pass
    try:
        from app.modules.knowledge_base.models import KnowledgeDocument
    except:
        pass
    try:
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
        print("DB tables checked/created - SUCCESS")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"DB exists, skipping: {e}")
            # Try again to create missing ones only
            try:
                SQLModel.metadata.create_all(bind=engine, checkfirst=True)
            except:
                pass
        else:
            print(f"DB init error: {e}")
            raise
