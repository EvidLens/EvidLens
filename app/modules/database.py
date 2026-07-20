import os
import redis
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
redis_client = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db():
    return get_session()

# ============ ADD THESE 2 MODELS ============
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, nullable=True) # format: +2547xxxxxxx
    name = Column(String, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    message = Column(Text)
    type = Column(String) # info, alert, trending_alert
    channel = Column(String) # in_app, email, sms, whatsapp
    status = Column(String) # sent, failed, in_app_saved
    created_at = Column(DateTime, default=datetime.utcnow)

from sqlmodel import SQLModel

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
