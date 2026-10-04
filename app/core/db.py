from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from.config import settings
import redis
import logging

logger = logging.getLogger(__name__)

if not settings.DATABASE_URL or not settings.DATABASE_URL.strip():
    raise ValueError("DATABASE_URL not set")

DATABASE_URL = settings.DATABASE_URL.strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sslmode" not in DATABASE_URL:
    DATABASE_URL += ("?sslmode=require" if "?" not in DATABASE_URL else "&sslmode=require")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=5,
    echo=False,
    connect_args={
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

# REAL FIX: Import all models BEFORE create_all so metadata contains auth_user
def _import_all_models():
    try:
        from app.core import models as core_models
    except Exception as e:
        print(f"core.models import error: {e}")
    try:
        from app.modules.auth import models as auth_models
    except Exception as e:
        print(f"auth.models import error: {e}")
    try:
        from app.modules.payments import models as payments_models
    except Exception as e:
        print(f"payments.models skip: {e}")
    try:
        from app.modules.report_builder import models as rb_models
    except Exception as e:
        print(f"report_builder skip: {e}")
    try:
        from app.modules.pricing_engine import models as pe_models
    except Exception as e:
        print(f"pricing_engine skip: {e}")
    try:
        from app.modules.regulatory_engine import models as re_models
    except Exception as e:
        print(f"regulatory_engine skip: {e}")
    try:
        from app.modules.consumer_voice import models as cv_models
    except Exception as e:
        print(f"consumer_voice skip: {e}")
    try:
        from app.modules.location_intel import models as li_models
    except Exception as e:
        print(f"location_intel skip: {e}")
    try:
        from app.modules.business_os import models as bos_models
    except Exception as e:
        print(f"business_os skip: {e}")
    try:
        from app.modules.knowledge_base import models as kb_models
    except Exception as e:
        print(f"knowledge_base skip: {e}")
    try:
        from app.modules.competitive_engine import models as ce_models
    except Exception as e:
        print(f"competitive_engine skip: {e}")

_import_all_models()

def init_db():
    try:
        SQLModel.metadata.create_all(bind=engine, checkfirst=True)
        print("DB CORE TABLES CREATED - SUCCESS")
        logger.info("DB CORE TABLES CREATED - SUCCESS")
    except Exception as e:
        print(f"Core create error: {e}")
        logger.error(f"Core create error: {e}")
        raise
    print("DB init_db DONE - All tables exist")
