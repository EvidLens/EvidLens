from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class KenyaLensSubscription(SQLModel, table=True):
    __tablename__ = "kenya_lens_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    plan_code: str
    status: str
    renews_at: Optional[datetime] = None
    api_credits: int = 0
    features_json: Optional[str] = None

class KenyaLensAlert(SQLModel, table=True):
    __tablename__ = "kenya_lens_alerts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    alert_type: str
    message: str
    is_read: bool = False
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class KenyaLensMember(SQLModel, table=True):
    __tablename__ = "kenya_lens_members"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    role: str = "member"
    status: str = "active"
    joined_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class KenyaLensApiUsage(SQLModel, table=True):
    __tablename__ = "kenya_lens_api_usage"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    endpoint: str
    credits_used: int = 1
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
