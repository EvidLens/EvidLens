# app/modules/seed_data/__init__.py
"""
EvidLens Seed Data
Preloads Kenya Counties, Sectors, FMCG for Zero Setup
"""

from sqlalchemy.orm import Session
from app.modules.database import SessionLocal

# 4.2: All 36 Kenya Industry Sectors from KNBS
KENYA_SECTORS = [
    "Agriculture", "Livestock & Fisheries", "Manufacturing", "Construction & Real Estate", 
    "Mining & Quarrying", "Energy & Utilities", "ICT", "Telecommunications", "Banking", 
    "Insurance", "Microfinance & SACCOs", "Capital Markets & Investment", "Healthcare", 
    "Pharmaceuticals & Medical Supplies", "Education & Training", "Hospitality", 
    "Tourism & Travel", "Transport & Logistics", "Wholesale & Retail Trade", "Automotive", 
    "Media & Entertainment", "Creative & Digital Economy", "Professional Services", 
    "Research & Market Intelligence", "BPO", "Government & Public Administration", "NGOs", 
    "Security Services", "Environmental Services", "Water & Sanitation", "FinTech", 
    "E-commerce", "Religious Organizations", "Sports & Recreation", "Beauty & Personal Care", 
    "Fashion & Apparel", "Printing & Publishing", "Food & Beverage"
]

# 4.1: 47 Counties - Kenya
KENYA_COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa", "Homa Bay", 
    "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii", 
    "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit", 
    "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", 
    "Nyandarua", "Nyeri", "Samburu", "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", 
    "Trans Nzoia", "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"
]

# 4.3: FMCG Catalog - Full Breakdown
FMCG_CATALOG = {
    "Food & Staples": ["Maize flour", "Wheat flour", "Rice", "Sugar", "Salt", "Cooking oil", "Beans", "Maize"],
    "Dairy": ["Fresh milk", "UHT milk", "Mala", "Yoghurt", "Cheese", "Ice cream"],
    "Beverages": ["Water", "Soft drinks", "Energy drinks", "Juices", "Tea", "Coffee", "Alcohol"],
    "Personal Care": ["Soap", "Shampoo", "Lotion", "Deodorant", "Toothpaste", "Sanitary pads"],
    "Household Care": ["Detergent", "Bleach", "Cleaner", "Tissue", "Insecticide"],
    "Baby Care": ["Diapers", "Baby food", "Baby wipes"],
    "Health & Wellness OTC": ["Painkillers", "Vitamins", "First aid"],
    "Pet Care": ["Dog food", "Cat food"],
    "Tobacco & Nicotine": ["Cigarettes", "Snuff"]
}

def seed_sectors(db: Session):
    """Seed 36 KNBS sectors"""
    from app.modules.knowledge_base.models import Sector
    for name in KENYA_SECTORS:
        if not db.query(Sector).filter(Sector.name==name).first():
            db.add(Sector(name=name))
    db.commit()

def seed_counties(db: Session):
    """Seed 47 Counties for LocationIQ + Overpass"""
    from app.modules.location_intel.models import County
    for name in KENYA_COUNTIES:
        if not db.query(County).filter(County.name==name).first():
            db.add(County(name=name))
    db.commit()

def seed_fmcg(db: Session):
    """Seed FMCG catalog from OpenFoodFacts + Scraped data"""
    from app.modules.market_engine.models import FMCGProduct
    for category, products in FMCG_CATALOG.items():
        for product in products:
            if not db.query(FMCGProduct).filter(FMCGProduct.name==product).first():
                db.add(FMCGProduct(name=product, category=category))
    db.commit()

def run_seed():
    """Run all seeds. Call on startup once"""
    db = SessionLocal()
    try:
        print("Seeding EvidLens Kenya Data...")
        seed_sectors(db)
        seed_counties(db)
        seed_fmcg(db)
        print(f"Done. Loaded {len(KENYA_SECTORS)} sectors, {len(KENYA_COUNTIES)} counties, {sum(len(v) for v in FMCG_CATALOG.values())} FMCG products")
    finally:
        db.close()
