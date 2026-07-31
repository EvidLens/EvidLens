from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, Column, Index
from sqlalchemy.sql import func
from sqlalchemy import JSON
from pydantic import BaseModel

KENYA_COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa", "Homa Bay", "Isiolo",
    "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui",
    "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit", "Meru", "Migori",
    "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri",
    "Samburu", "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"
]

KENYA_SUBCOUNTIES = {
    "Mombasa": ["Changamwe", "Jomvu", "Kisauni", "Nyali", "Likoni", "Mvita"],
    "Kwale": ["Msambweni", "Lunga Lunga", "Matuga", "Kinango"],
    "Kilifi": ["Kilifi North", "Kilifi South", "Kaloleni", "Rabai", "Ganze", "Malindi", "Magarini"],
    "Tana River": ["Garsen", "Galole", "Bura"],
    "Lamu": ["Lamu East", "Lamu West"],
    "Taita-Taveta": ["Taveta", "Wundanyi", "Mwatate", "Voi"],
    "Garissa": ["Garissa Township", "Balambala", "Lagdera", "Dadaab", "Fafi", "Ijara"],
    "Wajir": ["Wajir North", "Wajir East", "Tarbaj", "Wajir West", "Eldas", "Wajir South"],
    "Mandera": ["Mandera West", "Banisa", "Mandera North", "Mandera East", "Lafey", "Kutulo"],
    "Marsabit": ["Moyale", "North Horr", "Saku", "Laisamis"],
    "Isiolo": ["Isiolo North", "Isiolo South", "Garba Tulla"],
    "Meru": ["Imenti North", "Imenti South", "Central Imenti", "Buuri", "Tigania East", "Tigania West", "Igembe North", "Igembe South", "Igembe Central"],
    "Tharaka-Nithi": ["Nithi (Chuka/Igambang'ombe)", "Maara", "Tharaka"],
    "Embu": ["Manyatta", "Runyenjes", "Mbeere South (Gachoka)", "Mbeere North (Siakago)"],
    "Kitui": ["Kitui Central", "Kitui West", "Kitui Rural", "Kitui South", "Mutomo", "Mwingi North", "Mwingi Central", "Mwingi West"],
    "Machakos": ["Machakos Town", "Mavoko", "Kathiani", "Matungulu", "Kangundo", "Mwala", "Yatta", "Masinga"],
    "Makueni": ["Makueni", "Mbooni", "Kibwezi West", "Kibwezi East", "Kaiti", "Kilome"],
    "Nyandarua": ["Kinangop", "Kipipiri", "Ol Kalou", "Ol Jorok", "Ndaragwa"],
    "Nyeri": ["Nyeri Town", "Tetu", "Kieni", "Mathira", "Othaya", "Mukurweini"],
    "Kirinyaga": ["Kirinyaga Central", "Kirinyaga East (Gichugu)", "Kirinyaga West (Ndia)", "Mwea East", "Mwea West"],
    "Murang'a": ["Kiharu", "Kangema", "Mathioya", "Kigumo", "Maragwa", "Kandara", "Gatanga"],
    "Kiambu": ["Thika Town", "Ruiru", "Githunguri", "Kiambu", "Kiambaa", "Kabete", "Kikuyu", "Limuru", "Lari", "Gatundu South", "Gatundu North", "Juja"],
    "Turkana": ["Turkana Central", "Turkana North", "Turkana West", "Turkana South", "Turkana East", "Loima"],
    "West Pokot": ["Kapenguria", "Sigor", "Kacheliba", "Pokot South"],
    "Samburu": ["Samburu Central", "Samburu North", "Samburu East"],
    "Trans Nzoia": ["Saboti", "Kiminini", "Cherangany", "Kwanza", "Endebess"],
    "Uasin Gishu": ["Eldoret East", "Eldoret West", "Kesses", "Moiben", "Soy", "Turbo"],
    "Elgeyo-Marakwet": ["Keiyo North", "Keiyo South", "Marakwet East", "Marakwet West"],
    "Nandi": ["Nandi Hills", "Emgwen", "Chesumei", "Aldai", "Mosop", "Nandi Central"],
    "Baringo": ["Baringo Central", "Baringo North", "Baringo South", "Mogotio", "Tiaty", "Eldama Ravine"],
    "Laikipia": ["Laikipia East", "Laikipia West", "Laikipia North", "Nyahururu", "Ol Moran"],
    "Nakuru": ["Nakuru Town East", "Nakuru Town West", "Naivasha", "Gilgil", "Molo", "Njoro", "Kuresoi North", "Kuresoi South", "Rongai", "Subukia"],
    "Narok": ["Narok North", "Narok South", "Narok East", "Narok West", "Transmara West", "Transmara East"],
    "Kajiado": ["Kajiado Central", "Kajiado North", "Kajiado East", "Kajiado West", "Kajiado South"],
    "Kericho": ["Ainamoi", "Belgut", "Bureti", "Kipkelion East", "Kipkelion West", "Soin/Sigowet"],
    "Bomet": ["Bomet Central", "Bomet East", "Chepalungu", "Konoin", "Sotik"],
    "Kakamega": ["Lurambi", "Mumias East", "Mumias West", "Matungu", "Navakholo", "Khwisero", "Butere", "Shinyalu", "Ikolomani", "Lugari", "Likuyani"],
    "Vihiga": ["Vihiga", "Sabatia", "Hamisi", "Emuhaya", "Luanda"],
    "Bungoma": ["Kanduyi", "Bumula", "Kabuchai", "Kimilili", "Mt. Elgon", "Sirisia", "Tongaren", "Webuye East", "Webuye West"],
    "Busia": ["Teso North", "Teso South", "Nambale", "Matayos", "Butula", "Funyula", "Budalangi"],
    "Siaya": ["Alego Usonga", "Gem", "Ugenya", "Ugunja", "Bondo", "Rarieda"],
    "Kisumu": ["Kisumu Central", "Kisumu East", "Kisumu West", "Seme", "Nyando", "Muhoroni", "Nyakach"],
    "Homa Bay": ["Homa Bay Town", "Kasipul", "Kabondo Kasipul", "Karachuonyo", "Rangwe", "Ndhiwa", "Mbita", "Suba"],
    "Migori": ["Migori East", "Migori West", "Rongo", "Awendo", "Uriri", "Nyatike", "Kuria East", "Kuria West"],
    "Kisii": ["Kitutu Chache North", "Kitutu Chache South", "South Mugirango", "Bomachoge Borabu", "Bomachoge Chache", "Bobasi", "Nyaribari Chache", "Nyaribari Masaba", "Bonchari"],
    "Nyamira": ["West Mugirango", "North Mugirango", "Kitutu Masaba", "Borabu"],
    "Nairobi": ["Westlands", "Dagoretti North", "Dagoretti South", "Lang'ata", "Kibra", "Roysambu", "Kasarani", "Ruaraka", "Embakasi North", "Embakasi South", "Embakasi East", "Embakasi West", "Embakasi Central", "Makadara", "Kamukunji", "Starehe", "Mathare"]
}


class LocationGeo(SQLModel, table=True):
    __tablename__ = "location_geo"

    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = Field(max_length=20, index=True) # county, sub_county, ward, town
    name: str = Field(max_length=100, index=True)
    parent: Optional[str] = Field(default=None, max_length=100, index=True)
    lat: Optional[float] = Field(default=None)
    lng: Optional[float] = Field(default=None)

    __table_args__ = (
        Index('ix_geo_level_parent', 'level', 'parent'),
    )

class LocationComparison(SQLModel, table=True):
    __tablename__ = "location_comparisons"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(max_length=100, index=True)
    location_type: str = Field(default="county", max_length=20)
    location_a: str = Field(max_length=100, index=True)
    location_b: str = Field(max_length=100, index=True)
    comparison_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    calculated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

    __table_args__ = (
        Index('ix_comparison_sector_locations', 'sector', 'location_type', 'location_a', 'location_b'),
    )

class OpportunityHeatmap(SQLModel, table=True):
    __tablename__ = "opportunity_heatmaps"

    id: Optional[int] = Field(default=None, primary_key=True)
    sector: str = Field(max_length=100, index=True)
    country: str = Field(default="Kenya", max_length=50)
    county: Optional[str] = Field(default=None, max_length=100, index=True)
    sub_county: Optional[str] = Field(default=None, max_length=100, index=True)
    ward: Optional[str] = Field(default=None, max_length=100, index=True)
    town: Optional[str] = Field(default=None, max_length=100, index=True)
    opportunity_score: float
    lat: Optional[float] = Field(default=None)
    lng: Optional[float] = Field(default=None)
    factors: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})

    __table_args__ = (
        Index('ix_heatmap_geo', 'sector', 'county', 'sub_county', 'ward', 'town'),
    )

class PriceArbitrage(SQLModel, table=True):
    __tablename__ = "price_arbitrage"

    id: Optional[int] = Field(default=None, primary_key=True)
    product: str = Field(max_length=255, index=True)
    location_type: str = Field(max_length=20)
    county_from: Optional[str] = Field(default=None, max_length=100)
    county_to: Optional[str] = Field(default=None, max_length=100)
    sub_county_from: Optional[str] = Field(default=None, max_length=100)
    sub_county_to: Optional[str] = Field(default=None, max_length=100)
    town_from: Optional[str] = Field(default=None, max_length=100)
    town_to: Optional[str] = Field(default=None, max_length=100)
    price_gap_kes: float
    margin_percent: float
    calculated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})

    __table_args__ = (
        Index('ix_arbitrage_product_location', 'product', 'location_type'),
    )

class LocationComparisonResponse(BaseModel):
    sector: str
    location_type: str
    location_a: str
    location_b: str
    comparison_data: dict

    class Config:
        from_attributes = True
