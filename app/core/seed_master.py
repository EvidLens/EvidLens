import logging
import os
from sqlmodel import Session, select, func
from app.core.db import engine
from app.core.models import Company, GeoData

logger = logging.getLogger(__name__)

SEED_ENABLED = os.getenv("SEED_ENABLED", "false").lower() in ("1", "true", "yes")

COUNTIES = [
    ("001", "Mombasa", "Coast", "Mombasa"),
    ("002", "Kwale", "Coast", "Kwale"),
    ("003", "Kilifi", "Coast", "Kilifi"),
    ("004", "Tana River", "Coast", "Hola"),
    ("005", "Lamu", "Coast", "Lamu"),
    ("006", "Taita-Taveta", "Coast", "Voi"),
    ("007", "Garissa", "North Eastern", "Garissa"),
    ("008", "Wajir", "North Eastern", "Wajir"),
    ("009", "Mandera", "North Eastern", "Mandera"),
    ("010", "Marsabit", "Eastern", "Marsabit"),
    ("011", "Isiolo", "Eastern", "Isiolo"),
    ("012", "Meru", "Eastern", "Meru"),
    ("013", "Tharaka-Nithi", "Eastern", "Chuka"),
    ("014", "Embu", "Eastern", "Embu"),
    ("015", "Kitui", "Eastern", "Kitui"),
    ("016", "Machakos", "Eastern", "Machakos"),
    ("017", "Makueni", "Eastern", "Wote"),
    ("018", "Nyandarua", "Central", "Ol Kalou"),
    ("019", "Nyeri", "Central", "Nyeri"),
    ("020", "Kirinyaga", "Central", "Kerugoya"),
    ("021", "Murang'a", "Central", "Murang'a"),
    ("022", "Kiambu", "Central", "Kiambu"),
    ("023", "Turkana", "Rift Valley", "Lodwar"),
    ("024", "West Pokot", "Rift Valley", "Kapenguria"),
    ("025", "Samburu", "Rift Valley", "Maralal"),
    ("026", "Trans Nzoia", "Rift Valley", "Kitale"),
    ("027", "Uasin Gishu", "Rift Valley", "Eldoret"),
    ("028", "Elgeyo-Marakwet", "Rift Valley", "Iten"),
    ("029", "Nandi", "Rift Valley", "Kapsabet"),
    ("030", "Baringo", "Rift Valley", "Kabarnet"),
    ("031", "Laikipia", "Rift Valley", "Rumuruti"),
    ("032", "Nakuru", "Rift Valley", "Nakuru"),
    ("033", "Narok", "Rift Valley", "Narok"),
    ("034", "Kajiado", "Rift Valley", "Kajiado"),
    ("035", "Kericho", "Rift Valley", "Kericho"),
    ("036", "Bomet", "Rift Valley", "Bomet"),
    ("037", "Kakamega", "Western", "Kakamega"),
    ("038", "Vihiga", "Western", "Mbale"),
    ("039", "Bungoma", "Western", "Bungoma"),
    ("040", "Busia", "Western", "Busia"),
    ("041", "Siaya", "Nyanza", "Siaya"),
    ("042", "Kisumu", "Nyanza", "Kisumu"),
    ("043", "Homa Bay", "Nyanza", "Homa Bay"),
    ("044", "Migori", "Nyanza", "Migori"),
    ("045", "Kisii", "Nyanza", "Kisii"),
    ("046", "Nyamira", "Nyanza", "Nyamira"),
    ("047", "Nairobi", "Nairobi", "Nairobi"),
]

COMPANIES = [
    ("Safaricom PLC", "Telcos & ISPs", "Nairobi"),
    ("Equity Bank Kenya", "Banks", "Nairobi"),
    ("KCB Group", "Banks", "Nairobi"),
    ("Co-operative Bank", "Banks", "Nairobi"),
    ("ABSA Bank Kenya", "Banks", "Nairobi"),
    ("NCBA Group", "Banks", "Nairobi"),
    ("Stanbic Bank Kenya", "Banks", "Nairobi"),
    ("Diamond Trust Bank", "Banks", "Nairobi"),
    ("I&M Bank", "Banks", "Nairobi"),
    ("Family Bank", "Banks", "Nairobi"),
    ("Britam Holdings", "Insurance & HMOs", "Nairobi"),
    ("Jubilee Insurance", "Insurance & HMOs", "Nairobi"),
    ("CIC Insurance", "Insurance & HMOs", "Nairobi"),
    ("Sanlam Kenya", "Insurance & HMOs", "Nairobi"),
    ("Kenya Re", "Insurance & HMOs", "Nairobi"),
    ("East African Breweries", "FMCG - Food & Beverage", "Nairobi"),
    ("Kenya Airways", "Aviation & Airlines", "Nairobi"),
    ("KenGen", "Energy - Electricity Generation", "Nairobi"),
    ("Kenya Power", "Energy - Utilities & Water", "Nairobi"),
    ("Kakuzi PLC", "Agribusiness - Crops & Farming", "Murang'a"),
    ("Sasini PLC", "Agribusiness - Crops & Farming", "Kiambu"),
    ("Williamson Tea", "Agribusiness - Crops & Farming", "Kericho"),
    ("Kapchorua Tea", "Agribusiness - Crops & Farming", "Nandi"),
    ("Limuru Tea", "Agribusiness - Crops & Farming", "Kiambu"),
    ("TotalEnergies Kenya", "Energy - Oil & Gas", "Nairobi"),
    ("Bamburi Cement", "Manufacturing - Construction Materials", "Mombasa"),
    ("East African Portland Cement", "Manufacturing - Construction Materials", "Machakos"),
    ("Nation Media Group", "Media & Broadcasting", "Nairobi"),
    ("Standard Group", "Media & Broadcasting", "Nairobi"),
    ("Royal Media Services", "Media & Broadcasting", "Nairobi"),
    ("Nairobi Securities Exchange", "Capital Markets & Investment Banks", "Nairobi"),
    ("Centum Investment", "Capital Markets & Investment Banks", "Nairobi"),
    ("TransCentury", "Construction & Infrastructure", "Nairobi"),
    ("Car & General", "Automotive - Dealerships", "Nairobi"),
    ("Sameer Africa", "Manufacturing - Automotive & Assembly", "Nairobi"),
    ("Naivas Supermarket", "Retail - Supermarkets & Chains", "Nairobi"),
    ("Quickmart", "Retail - Supermarkets & Chains", "Nairobi"),
    ("Carrefour Kenya", "Retail - Supermarkets & Chains", "Nairobi"),
    ("Brookside Dairy", "Agribusiness - Livestock & Dairy", "Kiambu"),
    ("New Kenya Co-operative Creameries", "Agribusiness - Livestock & Dairy", "Nakuru"),
    ("Bidco Africa", "Manufacturing - Food Processing", "Nairobi"),
    ("Unilever Kenya", "FMCG - Personal Care & Household", "Nairobi"),
    ("PZ Cussons", "FMCG - Personal Care & Household", "Nairobi"),
    ("BAT Kenya", "Manufacturing - Food Processing", "Nairobi"),
    ("Crown Paints", "Manufacturing - Chemicals & Plastics", "Nairobi"),
    ("Kenya Pipeline", "Energy - Oil & Gas", "Nairobi"),
    ("Mumias Sugar", "Agribusiness - Crops & Farming", "Kakamega"),
    ("Nzoia Sugar", "Agribusiness - Crops & Farming", "Bungoma"),
]

def get_counties():
    return [name for _, name, _, _ in COUNTIES]

def get_counties_expanded():
    return [{"code": code, "name": name, "region": region, "headquarters": hq} for code, name, region, hq in COUNTIES]

def get_companies():
    return list(COMPANIES)

def seed_counties(db: Session):
    inserted = 0
    existing = {r.name for r in db.exec(select(GeoData).where(GeoData.type == "county")).all()}
    for code, name, region, hq in COUNTIES:
        if name not in existing:
            row = GeoData(name=name, type="county", county=name)
            if hasattr(row, "code"):
                row.code = code
            if hasattr(row, "region"):
                row.region = region
            if hasattr(row, "headquarters"):
                row.headquarters = hq
            db.add(row)
            inserted += 1
    if inserted:
        db.commit()
    return inserted

def seed_companies(db: Session = None):
    close = False
    if db is None:
        db = Session(engine)
        close = True
    try:
        inserted = 0
        existing = {r.name for r in db.exec(select(Company)).all()}
        for name, sector, county in COMPANIES:
            if name not in existing:
                db.add(Company(name=name, sector=sector, county=county))
                inserted += 1
        if inserted:
            db.commit()
        return {"status": "seeded", "inserted": inserted}
    finally:
        if close:
            db.close()

def seed_all():
    if not SEED_ENABLED:
        logger.info("seed_all() disabled - counties/companies only seed when SEED_ENABLED=true, prices/news never seeded")
        return {"status": "disabled", "message": "Seed disabled. Counties/companies are reference data, prices/news come only from live scrapers.", "inserted": 0, "counties_kept": len(COUNTIES), "companies_kept": len(COMPANIES)}
    inserted = 0
    with Session(engine) as db:
        inserted += seed_counties(db)
        inserted += seed_companies(db)["inserted"]
    try:
        from app.modules.jobs.scrapers import scrape_kpin_prices, fetch_real_news
        inserted += int(scrape_kpin_prices() or 0)
        inserted += int(fetch_real_news() or 0)
    except Exception as e:
        logger.warning("Live scraper seed failed, no fake rows inserted: %s", e)
    try:
        from app.core.seed_master_plans import seed_plans_modules
        with Session(engine) as db:
            seed_plans_modules(db)
    except Exception as e:
        logger.warning("seed_plans_modules failed: %s", e)
    return {"status": "seeded", "inserted": inserted, "counties_kept": len(COUNTIES), "companies_kept": len(COMPANIES)}

def seed_prices():
    return {"status": "disabled", "inserted": 0, "message": "Prices come only from live KPIN scraper, never seeded."}

def seed_metrics():
    return {"status": "disabled", "inserted": 0, "message": "Metrics come only from live KPIN scraper."}

def seed_news():
    if not SEED_ENABLED:
        return {"status": "disabled", "inserted": 0}
    try:
        from app.modules.jobs.scrapers import fetch_real_news
        return {"status": "seeded_from_live_sources", "inserted": int(fetch_real_news() or 0)}
    except Exception as e:
        logger.warning("News scraper failed: %s", e)
        return {"status": "failed", "inserted": 0}

if __name__ == "__main__":
    print(seed_all())
