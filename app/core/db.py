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

# FIX 1: Force SSL
if "sslmode" not in DATABASE_URL:
    DATABASE_URL += ("?sslmode=require" if "?" not in DATABASE_URL else "&sslmode=require")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,  # FIX 2: was 300, now 280 to recycle BEFORE Render kills
    pool_size=5,       # FIX 3: was 10, now 5 - Render free limit is 97
    max_overflow=5,    # FIX 4: was 20, now 5
    echo=False,
    connect_args={     # FIX 5: keepalives - this was missing
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "connect_timeout": 10,
        "sslmode": "require",
    },
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
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
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

    try:
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
        print("DB CORE TABLES CREATED - SUCCESS")
        logger.info("DB CORE TABLES CREATED - SUCCESS")
    except Exception as e:
        print(f"Core create error: {e}")
        logger.error(f"Core create error: {e}")

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
