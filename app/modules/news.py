from sqlmodel import SQLModel, Field
from datetime import datetime

class NewsArticle(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product: str
    title: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
