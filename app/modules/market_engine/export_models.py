from sqlmodel import SQLModel, Field
from typing import Optional

class TradeFlow(SQLModel, table=True):
    __tablename__ = "trade_flows"
    id: Optional[int] = Field(default=None, primary_key=True)
    hs: str = Field(index=True)  # HS6 e.g. 090230
    product: str = Field(index=True)
    reporter: str = Field(default="Kenya", index=True)
    reporter_code: int = Field(default=404)
    partner: str = Field(index=True)  # destination
    partner_code: int = Field(default=0)
    year: int = Field(index=True)
    flow: str = Field(default="X")  # X=export, M=import
    value_usd: float = Field(default=0)  # USD
    qty_kg: float = Field(default=0)
    unit_value: float = Field(default=0)  # USD/kg
    growth_pct: float = Field(default=0)
    kenya_share_pct: float = Field(default=0)
    tariff_pct: float = Field(default=0)
    distance_km: int = Field(default=7000)
    counties: str = Field(default="")
    source: str = Field(default="UN Comtrade")
    updated_at: str = Field(default="")

class ProductCatalogue(SQLModel, table=True):
    __tablename__ = "product_catalogue"
    hs: str = Field(primary_key=True)
    name: str = Field(index=True)
    hs4: str = Field(index=True)
    counties: str = Field(default="")
    category: str = Field(default="")
