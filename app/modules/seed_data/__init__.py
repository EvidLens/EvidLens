import json
import os
from sqlalchemy.orm import Session
from app.modules.db import SessionLocal
from app.models.sector import Sector, County, Product

SEED_DIR = os.path.dirname(__file__)

def load_json(filename):
    path = os.path.join(SEED_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_seed():
    db: Session = SessionLocal()
    try:
        print("Seeding EvidLens Kenya Data...")

        # 1. Seed Sectors
        sectors_data = load_json("kenya_sectors.json")
        for item in sectors_data:
            exists = db.query(Sector).filter(Sector.id == item["id"]).first()
            if not exists:
                db.add(Sector(**item))

        # 2. Seed Counties  
        counties_data = load_json("kenya_counties.json")
        for item in counties_data:
            exists = db.query(County).filter(County.id == item["id"]).first()
            if not exists:
                db.add(County(**item))

        # 3. Seed FMCG Products
        products_data = load_json("fmcg_catalog.json")
        for item in products_data:
            exists = db.query(Product).filter(Product.id == item["id"]).first()
            if not exists:
                db.add(Product(**item))

        db.commit()
        print(f"Done. Loaded {len(sectors_data)} sectors, {len(counties_data)} counties, {len(products_data)} FMCG products")
        print("EvidLens Ready. All 9 Lanes loaded.")
        
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()
