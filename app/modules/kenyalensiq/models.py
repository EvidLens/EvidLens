    from sqlmodel import SQLModel, Field
    from datetime import datetime

    class KenyaLensSubscription(SQLModel, table=True):
        __tablename__ = "kenya_lens_subscriptions"
        id: int | None = Field(default=None, primary_key=True)
        user_id: int
        plan_code: str
        status: str
        renews_at: datetime | None = None
        api_credits: int = 0
        features_json: str | None = None
