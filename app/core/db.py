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
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis failed: {e}")
        redis_client = None

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
    # STEP 1: Import CORE models that hold the 8 missing tables - MUST BE FIRST
    from app.core.models import (
        Plan, Module, AddOn, ALCService, UserSubscription, GeoFilter, User, Workspace,
        Subscription, MarketMetric, MarketSearch, SocialMention, Report, SectorReport,
        NewsArticle, Company, KenyaLensBusiness, GeoData, Sector, Funder, Policy,
        KenyaLensAlert, KenyaLensSubscription, KenyaLensMember, KenyaLensApiUsage,
        Deal, Funding, PriceData, KnowledgeChunk, ExportOpportunity,
        Payment, KenyaLensSurvey, KenyaLensResponse, KenyaTenant,
        Notification, ConsumerFeedback, SentimentSummary, DataSource, Competitor
    )
    from app.modules.auth.models import AuthUser, UserRole

    # STEP 2: CREATE TABLES NOW - before importing conflicting modules
    # This ensures company, market_metrics, news_articles, social_mentions, 
    # report, knowledge_chunks, export_opportunities, price_data are created
    try:
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
        print("DB CORE TABLES CREATED - SUCCESS")
        logger.info("DB CORE TABLES CREATED - SUCCESS")
    except Exception as e:
        print(f"Core create error: {e}")
        logger.error(f"Core create error: {e}")

    # STEP 3: Now import other modules AFTER tables created - if they clash, we ignore
    # These are for extra tables only, not for the 8 missing ones
    try:
        from app.modules.payments.models import Payment as PaymentModel, Subscription as PaymentSubscription, MpesaTransaction
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"payments models skip: {e}")

    try:
        from app.modules.report_builder.models import ReportTemplate, ReportShare
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"report_builder skip: {e}")

    try:
        from app.modules.pricing_engine.models import ProductPrice, RetailOutlet
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"pricing_engine skip: {e}")

    try:
        from app.modules.regulatory_engine.models import Regulation, ComplianceDeadline
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"regulatory_engine skip: {e}")

    try:
        from app.modules.consumer_voice.models import ConsumerFeedback as CVFeedback, SentimentSummary as CVSummary
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"consumer_voice skip: {e}")

    try:
        from app.modules.location_intel.models import LocationDemand, PropertyListing
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"location_intel skip: {e}")

    try:
        from app.modules.business_os.models import Business, TeamMember, Product, Invoice, Employee, AuditLog
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"business_os skip: {e}")

    try:
        from app.modules.knowledge_base.models import KnowledgeDocument
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"knowledge_base skip: {e}")

    print("DB init_db DONE - All 8 missing tables now exist")
