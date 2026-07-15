import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./evidlens_dev.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.modules.auth.models import User, UserRole
    from app.modules.models import Sector, County, CoreProduct
    from app.modules.payments.models import Payment, Subscription, MpesaTransaction
    from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
    from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric
    from app.modules.core.models import Plan, Module, Sector, AddOn, ALCService, UserSubscription, GeoFilter
    Base.metadata.create_all(bind=engine)
get_db = get_session
