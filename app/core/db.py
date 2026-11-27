from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from typing import Generator, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def build_database_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        raise ValueError("DATABASE_URL not set")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("sqlite"):
        return url
    if "sslmode" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"
    return url

DATABASE_URL = build_database_url(settings.DATABASE_URL or settings.DEV_DATABASE_URL)
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
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

def get_redis_client():
    try:
        import redis
    except Exception:
        return None
    url = settings.effective_redis_url
    if not url:
        return None
    try:
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable, continuing without cache: %s", e)
        return None

redis_client = get_redis_client()

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def get_db() -> Generator[Session, None, None]:
    yield from get_session()

def _import_all_models():
    modules = [
        "app.core.models",
        "app.modules.auth.models",
        "app.modules.wallet.models",
        "app.modules.payments.models",
        "app.modules.report_builder.models",
        "app.modules.pricing_engine.models",
        "app.modules.regulatory_engine.models",
        "app.modules.consumer_voice.models",
        "app.modules.location_intel.models",
        "app.modules.business_os.models",
        "app.modules.knowledge_base.models",
        "app.modules.competitive_engine.models",
    ]
    for path in modules:
        try:
            __import__(path)
        except ModuleNotFoundError:
            logger.warning("Model module not found, skipping: %s", path)
        except Exception as e:
            logger.exception("Model import failed: %s - %s", path, e)
            raise

def init_db():
    _import_all_models()
    tables = list(SQLModel.metadata.tables.keys())
    logger.info("Tables to create: %s", tables)
    if "auth_user" not in SQLModel.metadata.tables:
        raise RuntimeError("auth_user table not registered in SQLModel metadata")
    SQLModel.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("DB tables created")
    if IS_SQLITE:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS report_id INTEGER"))
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS ip VARCHAR"))
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_agent VARCHAR"))
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
            conn.execute(text("ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_user_id_fkey"))
            conn.execute(text("ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL"))
        logger.info("audit_logs columns fixed")
    except Exception as e:
        logger.warning("audit_logs fix skipped: %s", e)

    # --- Fix workspace FKs: workspaces -> user should be workspaces -> auth_user ---
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(
                "SELECT conname, conrelid::regclass::text AS tbl, a.attname AS col "
                "FROM pg_constraint c "
                "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey) "
                "WHERE c.contype = 'f' AND c.confrelid = 'user'::regclass "
                "AND conrelid::regclass::text ILIKE '%workspace%'"
            )).fetchall()
            for conname, tbl, col in rows:
                ref = "workspaces" if col == "workspace_id" else "auth_user"
                logger.info(f"Fixing FK {tbl}.{conname} ({col}) -> {ref}(id)")
                conn.execute(text(f"ALTER TABLE {tbl} DROP CONSTRAINT IF EXISTS {conname}"))
                conn.execute(text(f"ALTER TABLE {tbl} ADD CONSTRAINT {conname} FOREIGN KEY ({col}) REFERENCES {ref}(id) ON DELETE CASCADE"))
            if rows:
                logger.info(f"Workspace FKs fixed: {len(rows)}")
            else:
                logger.info("Workspace FKs: no FKs pointing to user found")
    except Exception as e:
        logger.warning("Workspace FK fix skipped: %s", e)
