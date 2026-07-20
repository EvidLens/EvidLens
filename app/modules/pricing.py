from sqlmodel import SQLModel, Field
from datetime import datetime

class PriceData(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_name: str
    county: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
