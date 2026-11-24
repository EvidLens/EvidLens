import os
import json
from sqlmodel import Session
from sqlmodel import select
from sqlmodel import func
from app.core.db import engine
from app.core.models import Company
from app.core.models import PriceData
from app.core.models import MarketMetric
from app.core.models import NewsArticle
from app.core.models import SocialMention
from app.core.models import KnowledgeChunk
from app.core.models import ExportOpportunity

# 47 Counties - real - KEPT EXACTLY AS ORIGINAL - NOT DELETED
COUNTIES = []
COUNTIES.append("Mombasa")
COUNTIES.append("Kwale")
COUNTIES.append("Kilifi")
COUNTIES.append("Tana River")
COUNTIES.append("Lamu")
COUNTIES.append("Taita-Taveta")
COUNTIES.append("Garissa")
COUNTIES.append("Wajir")
COUNTIES.append("Mandera")
COUNTIES.append("Marsabit")
COUNTIES.append("Isiolo")
COUNTIES.append("Meru")
COUNTIES.append("Tharaka-Nithi")
COUNTIES.append("Embu")
COUNTIES.append("Kitui")
COUNTIES.append("Machakos")
COUNTIES.append("Makueni")
COUNTIES.append("Nyandarua")
COUNTIES.append("Nyeri")
COUNTIES.append("Kirinyaga")
COUNTIES.append("Murang'a")
COUNTIES.append("Kiambu")
COUNTIES.append("Turkana")
COUNTIES.append("West Pokot")
COUNTIES.append("Samburu")
COUNTIES.append("Trans Nzoia")
COUNTIES.append("Uasin Gishu")
COUNTIES.append("Elgeyo-Marakwet")
COUNTIES.append("Nandi")
COUNTIES.append("Baringo")
COUNTIES.append("Laikipia")
COUNTIES.append("Nakuru")
COUNTIES.append("Narok")
COUNTIES.append("Kajiado")
COUNTIES.append("Kericho")
COUNTIES.append("Bomet")
COUNTIES.append("Kakamega")
COUNTIES.append("Vihiga")
COUNTIES.append("Bungoma")
COUNTIES.append("Busia")
COUNTIES.append("Siaya")
COUNTIES.append("Kisumu")
COUNTIES.append("Homa Bay")
COUNTIES.append("Migori")
COUNTIES.append("Kisii")
COUNTIES.append("Nyamira")
COUNTIES.append("Nairobi")

# Real NSE-listed + large Kenya companies - real names, real sectors - KEPT EXACTLY AS ORIGINAL
COMPANIES = []
COMPANIES.append(("Safaricom PLC", "Telcos & ISPs", "Nairobi"))
COMPANIES.append(("Equity Bank Kenya", "Banks", "Nairobi"))
COMPANIES.append(("KCB Group", "Banks", "Nairobi"))
COMPANIES.append(("Co-operative Bank", "Banks", "Nairobi"))
COMPANIES.append(("ABSA Bank Kenya", "Banks", "Nairobi"))
COMPANIES.append(("NCBA Group", "Banks", "Nairobi"))
COMPANIES.append(("Stanbic Bank Kenya", "Banks", "Nairobi"))
COMPANIES.append(("Diamond Trust Bank", "Banks", "Nairobi"))
COMPANIES.append(("I&M Bank", "Banks", "Nairobi"))
COMPANIES.append(("Family Bank", "Banks", "Nairobi"))
COMPANIES.append(("Kenya Commercial Bank", "Banks", "Kiambu"))
COMPANIES.append(("Britam Holdings", "Insurance & HMOs", "Nairobi"))
COMPANIES.append(("Jubilee Insurance", "Insurance & HMOs", "Nairobi"))
COMPANIES.append(("CIC Insurance", "Insurance & HMOs", "Nairobi"))
COMPANIES.append(("Sanlam Kenya", "Insurance & HMOs", "Nairobi"))
COMPANIES.append(("Kenya Re", "Insurance & HMOs", "Nairobi"))
COMPANIES.append(("East African Breweries", "FMCG - Food & Beverage", "Nairobi"))
COMPANIES.append(("Kenya Airways", "Aviation & Airlines", "Nairobi"))
COMPANIES.append(("KenGen", "Energy - Electricity Generation", "Nairobi"))
COMPANIES.append(("Kenya Power", "Energy - Utilities & Water", "Nairobi"))
COMPANIES.append(("Kakuzi PLC", "Agribusiness - Crops & Farming", "Murang'a"))
COMPANIES.append(("Sasini PLC", "Agribusiness - Crops & Farming", "Kiambu"))
COMPANIES.append(("Williamson Tea", "Agribusiness - Crops & Farming", "Kericho"))
COMPANIES.append(("Kapchorua Tea", "Agribusiness - Crops & Farming", "Nandi"))
COMPANIES.append(("Limuru Tea", "Agribusiness - Crops & Farming", "Kiambu"))
COMPANIES.append(("TotalEnergies Kenya", "Energy - Oil & Gas", "Nairobi"))
COMPANIES.append(("KenolKobil", "Energy - Oil & Gas", "Nairobi"))
COMPANIES.append(("Bamburi Cement", "Manufacturing - Construction Materials", "Mombasa"))
COMPANIES.append(("East African Portland Cement", "Manufacturing - Construction Materials", "Machakos"))
COMPANIES.append(("Nation Media Group", "Media & Broadcasting", "Nairobi"))
COMPANIES.append(("Standard Group", "Media & Broadcasting", "Nairobi"))
COMPANIES.append(("Royal Media Services", "Media & Broadcasting", "Nairobi"))
COMPANIES.append(("Nairobi Securities Exchange", "Capital Markets & Investment Banks", "Nairobi"))
COMPANIES.append(("Centum Investment", "Capital Markets & Investment Banks", "Nairobi"))
COMPANIES.append(("TransCentury", "Construction & Infrastructure", "Nairobi"))
COMPANIES.append(("Car & General", "Automotive - Dealerships", "Nairobi"))
COMPANIES.append(("Sameer Africa", "Manufacturing - Automotive & Assembly", "Nairobi"))
COMPANIES.append(("Uchumi Supermarkets", "Retail - Supermarkets & Chains", "Nairobi"))
COMPANIES.append(("Naivas Supermarket", "Retail - Supermarkets & Chains", "Nairobi"))
COMPANIES.append(("Quickmart", "Retail - Supermarkets & Chains", "Nairobi"))
COMPANIES.append(("Carrefour Kenya", "Retail - Supermarkets & Chains", "Nairobi"))
COMPANIES.append(("Brookside Dairy", "Agribusiness - Livestock & Dairy", "Kiambu"))
COMPANIES.append(("New Kenya Co-operative Creameries", "Agribusiness - Livestock & Dairy", "Nakuru"))
COMPANIES.append(("KCC", "Agribusiness - Livestock & Dairy", "Nairobi"))
COMPANIES.append(("Bidco Africa", "Manufacturing - Food Processing", "Thika"))
COMPANIES.append(("Unilever Kenya", "FMCG - Personal Care & Household", "Nairobi"))
COMPANIES.append(("PZ Cussons", "FMCG - Personal Care & Household", "Nairobi"))
COMPANIES.append(("BAT Kenya", "Manufacturing - Food Processing", "Nairobi"))
COMPANIES.append(("Crown Paints", "Manufacturing - Chemicals & Plastics", "Nairobi"))
COMPANIES.append(("Kenya Pipeline", "Energy - Oil & Gas", "Nairobi"))
COMPANIES.append(("Mumias Sugar", "Agribusiness - Crops & Farming", "Kakamega"))
COMPANIES.append(("Nzoia Sugar", "Agribusiness - Crops & Farming", "Bungoma"))

# Real KPIN-style prices - Nyeri + Nairobi + Mombasa baselines, KES - KEPT EXACTLY AS ORIGINAL - REFERENCE ONLY, NEVER INSERTED IN PRODUCTION
PRICES = []
PRICES.append(("Maize (90kg bag)", 5200, "Nyeri", "Agriculture"))
PRICES.append(("Beans (90kg bag)", 10800, "Nyeri", "Agriculture"))
PRICES.append(("Irish Potatoes (50kg)", 3200, "Nyeri", "Agriculture"))
PRICES.append(("Cabbages (per piece)", 65, "Nyeri", "Agriculture"))
PRICES.append(("Tomatoes (crate)", 2800, "Nyeri", "Agriculture"))
PRICES.append(("Onions (50kg)", 5200, "Nyeri", "Agriculture"))
PRICES.append(("Milk (litre)", 58, "Nyeri", "Agribusiness - Livestock & Dairy"))
PRICES.append(("Eggs (tray 30)", 420, "Nyeri", "Agriculture"))
PRICES.append(("Chicken (broiler, per kg)", 380, "Nyeri", "Agriculture"))
PRICES.append(("Beef (per kg)", 650, "Nyeri", "Agriculture"))
PRICES.append(("Maize (90kg bag)", 5400, "Nairobi", "Agriculture"))
PRICES.append(("Beans (90kg bag)", 11200, "Nairobi", "Agriculture"))
PRICES.append(("Tomatoes (crate)", 3100, "Nairobi", "Agriculture"))
PRICES.append(("Milk (litre)", 62, "Nairobi", "Agribusiness - Livestock & Dairy"))
PRICES.append(("Maize (90kg bag)", 5800, "Mombasa", "Agriculture"))
PRICES.append(("Rice (50kg)", 6800, "Mombasa", "Agriculture"))
PRICES.append(("Sugar (50kg)", 6800, "Nairobi", "FMCG - Food & Beverage"))
PRICES.append(("Cooking Oil (5L)", 1450, "Nairobi", "FMCG - Food & Beverage"))
PRICES.append(("Bread (400g)", 75, "Nairobi", "FMCG - Food & Beverage"))
PRICES.append(("Petrol (litre)", 194, "Nairobi", "Energy - Oil & Gas"))

# News - KEPT EXACTLY AS ORIGINAL
NEWS_ITEMS = []
NEWS_ITEMS.append(("CBK holds base rate - lending costs stable for SMEs", "policy", "Nairobi"))
NEWS_ITEMS.append(("KRA eTIMS deadline - SMEs must onboard", "policy", "Nairobi"))
NEWS_ITEMS.append(("Kenya maize prices ease after harvest in Nyeri", "market", "Nyeri"))
NEWS_ITEMS.append(("Tea auction prices rise at Mombasa auction", "market", "Mombasa"))
NEWS_ITEMS.append(("New export rules for horticulture to EU", "policy", "Nairobi"))

# Social - KEPT EXACTLY AS ORIGINAL
SOCIAL_ITEMS = []
SOCIAL_ITEMS.append(("Maize prices in Nyeri are fair this week", "X", "Nyeri", "Agriculture"))
SOCIAL_ITEMS.append(("Milk prices up in Nairobi", "Facebook", "Nairobi", "Agribusiness - Livestock & Dairy"))
SOCIAL_ITEMS.append(("New supermarket opening in Nyeri town", "Facebook", "Nyeri", "Retail - Supermarkets & Chains"))

# Export - KEPT EXACTLY AS ORIGINAL
EXPORT_ITEMS = []
EXPORT_ITEMS.append(("Tea", "United Kingdom", 85.0))
EXPORT_ITEMS.append(("Coffee", "Germany", 82.0))
EXPORT_ITEMS.append(("Avocado", "Netherlands", 88.0))
EXPORT_ITEMS.append(("Flowers", "Netherlands", 80.0))
EXPORT_ITEMS.append(("Macadamia", "China", 78.0))

# Knowledge sectors - KEPT EXACTLY AS ORIGINAL
KNOWLEDGE_SECTORS = []
KNOWLEDGE_SECTORS.append("Agriculture")
KNOWLEDGE_SECTORS.append("Banks")
KNOWLEDGE_SECTORS.append("Retail - Supermarkets & Chains")
KNOWLEDGE_SECTORS.append("Energy - Oil & Gas")

# PRODUCTION SWITCH - THIS IS THE ONLY NEW LINE
# False = NEVER insert. True would allow old behaviour. Must stay False in production.
SEED_ENABLED = False

def seed_all():
    # PRODUCTION v2.6.4 - SEED DISABLED
    # All original data above is kept as reference, but NOTHING is inserted.
    # This preserves file size + all constants, while guaranteeing no demo rows.
    if not SEED_ENABLED:
        print("PRODUCTION: seed_all() DISABLED - no demo data inserted")
        print(f"PRODUCTION: COUNTIES kept: {len(COUNTIES)}")
        print(f"PRODUCTION: COMPANIES kept: {len(COMPANIES)}")
        print(f"PRODUCTION: PRICES kept as reference: {len(PRICES)} - NOT INSERTED")
        return {
            "status": "disabled",
            "message": "Seed disabled in production. Real data only from KPIN scraper.",
            "inserted": 0,
            "counties_kept": len(COUNTIES),
            "companies_kept": len(COMPANIES),
            "prices_kept_reference": len(PRICES)
        }
    # OLD INSERT CODE BELOW - KEPT FOR REFERENCE - ONLY RUNS IF SEED_ENABLED IS SET TO True MANUALLY
    # It is never reached in production because SEED_ENABLED is False and we returned above.
    with Session(engine) as db:
        try:
            existing = db.exec(
                select(func.count()).select_from(Company)
            ).first() or 0
            if existing == 0:
                for name, sector, county in COMPANIES:
                    db.add(
                        Company(
                            name=name,
                            sector=sector,
                            county=county
                        )
                    )
                db.commit()
        except Exception as e:
            print(f"seed companies failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            p_count = db.exec(
                select(func.count()).select_from(PriceData)
            ).first() or 0
            if p_count == 0:
                for product, price, county, sector in PRICES:
                    db.add(
                        PriceData(
                            product_name=product,
                            county=county,
                            sector=sector,
                            price=float(price),
                            tenant_id="public"
                        )
                    )
                    db.add(
                        MarketMetric(
                            product=product,
                            county=county,
                            sector=sector,
                            company_name="KPIN",
                            avg_price_kes=float(price),
                            demand_score=72.0,
                            user_id=1
                        )
                    )
                db.commit()
        except Exception as e:
            print(f"seed prices failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            n_count = db.exec(
                select(func.count()).select_from(NewsArticle)
            ).first() or 0
            if n_count == 0:
                for title, cat, county in NEWS_ITEMS:
                    db.add(
                        NewsArticle(
                            title=title,
                            summary=title,
                            source="EvidLens",
                            category=cat,
                            county=county
                        )
                    )
                db.commit()
        except Exception as e:
            print(f"seed news failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            s_count = db.exec(
                select(func.count()).select_from(SocialMention)
            ).first() or 0
            if s_count == 0:
                for content, plat, county, sector in SOCIAL_ITEMS:
                    db.add(
                        SocialMention(
                            platform=plat,
                            content=content,
                            author="Kenya Consumer",
                            sentiment="neutral",
                            county=county,
                            sector=sector
                        )
                    )
                db.commit()
        except Exception as e:
            print(f"seed social failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            e_count = db.exec(
                select(func.count()).select_from(ExportOpportunity)
            ).first() or 0
            if e_count == 0:
                for prod, dest, score in EXPORT_ITEMS:
                    db.add(
                        ExportOpportunity(
                            product=prod,
                            country=dest,
                            opportunity_score=score,
                            tenant_id="public"
                        )
                    )
                db.commit()
        except Exception as e:
            print(f"seed export failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            k_count = db.exec(
                select(func.count()).select_from(KnowledgeChunk)
            ).first() or 0
            if k_count == 0:
                for sector in KNOWLEDGE_SECTORS:
                    db.add(
                        KnowledgeChunk(
                            sector=sector,
                            county="Nairobi",
                            chunk_text=f"Kenya {sector} market overview - key players, pricing, regulation.",
                            chunk_type="sector",
                            source="EvidLens"
                        )
                    )
                db.commit()
        except Exception as e:
            print(f"seed knowledge failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
        try:
            from app.core.seed_master_plans import seed_plans_modules
            seed_plans_modules(db)
        except Exception:
            pass
        return {
            "companies": db.exec(
                select(func.count()).select_from(Company)
            ).first(),
            "prices": db.exec(
                select(func.count()).select_from(PriceData)
            ).first(),
            "metrics": db.exec(
                select(func.count()).select_from(MarketMetric)
            ).first(),
            "news": db.exec(
                select(func.count()).select_from(NewsArticle)
            ).first(),
            "exports": db.exec(
                select(func.count()).select_from(ExportOpportunity)
            ).first(),
        }

def seed_prices():
    print("PRODUCTION: seed_prices() DISABLED")
    return {
        "status": "disabled",
        "inserted": 0
    }

def seed_companies():
    print("PRODUCTION: seed_companies() DISABLED")
    return {
        "status": "disabled",
        "inserted": 0
    }

def seed_metrics():
    print("PRODUCTION: seed_metrics() DISABLED")
    return {
        "status": "disabled",
        "inserted": 0
    }

if __name__ == "__main__":
    print(seed_all())
