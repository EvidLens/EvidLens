from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class KenyaLensSubscription(SQLModel, table=True):
    __tablename__ = "kenya_lens_subscriptions"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    plan_code: str
    status: str
    renews_at: Optional[datetime] = None
    api_credits: int = 0
    features_json: Optional[str] = None


class KenyaLensAlert(SQLModel, table=True):
    __tablename__ = "kenya_lens_alerts"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    alert_type: str
    message: str
    is_read: bool = False
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class KenyaLensMember(SQLModel, table=True):
    __tablename__ = "kenya_lens_members"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    role: str = "member"
    status: str = "active"
    joined_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class KenyaLensApiUsage(SQLModel, table=True):
    __tablename__ = "kenya_lens_api_usage"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    endpoint: str
    credits_used: int = 1
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class SocialMention(SQLModel, table=True):
    __tablename__ = "social_mentions"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str
    content: str
    author: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
