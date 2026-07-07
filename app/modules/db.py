import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./evidlens_dev.db")

# Neon/Supabase Postgres for prod
# Example: postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {"sslmode": "require"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency for DB sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables. Run once on startup"""
    from app.modules.payments.models import Payment, Subscription, MpesaTransaction
    from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
    from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric
    Base.metadata.create_all(bind=engine)
