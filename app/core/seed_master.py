import os, json
from sqlmodel import Session, select, func
from app.core.db import engine
from app.core.models import Company, PriceData, MarketMetric, NewsArticle, SocialMention, KnowledgeChunk, ExportOpportunity

# 47 Counties - real
COUNTIES = ["Mombasa","Kwale","Kilifi","Tana River","Lamu","Taita-Taveta","Garissa","Wajir","Mandera","Marsabit","Isiolo","Meru","Tharaka-Nithi","Embu","Kitui","Machakos","Makueni","Nyandarua","Nyeri","Kirinyaga","Murang'a","Kiambu","Turkana","West Pokot","Samburu","Trans Nzoia","Uasin Gishu","Elgeyo-Marakwet","Nandi","Baringo","Laikipia","Nakuru","Narok","Kajiado","Kericho","Bomet","Kakamega","Vihiga","Bungoma","Busia","Siaya","Kisumu","Homa Bay","Migori","Kisii","Nyamira","Nairobi"]

# Real NSE-listed + large Kenya companies - real names, real sectors
COMPANIES = [
    ("Safaricom PLC","Telcos & ISPs","Nairobi"),("Equity Bank Kenya","Banks","Nairobi"),
    ("KCB Group","Banks","Nairobi"),("Co-operative Bank","Banks","Nairobi"),
    ("ABSA Bank Kenya","Banks","Nairobi"),("NCBA Group","Banks","Nairobi"),
    ("Stanbic Bank Kenya","Banks","Nairobi"),("Diamond Trust Bank","Banks","Nairobi"),
    ("I&M Bank","Banks","Nairobi"),("Family Bank","Banks","Nairobi"),
    ("Kenya Commercial Bank","Banks","Kiambu"),("Britam Holdings","Insurance & HMOs","Nairobi"),
    ("Jubilee Insurance","Insurance & HMOs","Nairobi"),("CIC Insurance","Insurance & HMOs","Nairobi"),
    ("Sanlam Kenya","Insurance & HMOs","Nairobi"),("Kenya Re","Insurance & HMOs","Nairobi"),
    ("East African Breweries","FMCG - Food & Beverage","Nairobi"),("Kenya Airways","Aviation & Airlines","Nairobi"),
    ("KenGen","Energy - Electricity Generation","Nairobi"),("Kenya Power","Energy - Utilities & Water","Nairobi"),
    ("Kakuzi PLC","Agribusiness - Crops & Farming","Murang'a"),("Sasini PLC","Agribusiness - Crops & Farming","Kiambu"),
    ("Williamson Tea","Agribusiness - Crops & Farming","Kericho"),("Kapchorua Tea","Agribusiness - Crops & Farming","Nandi"),
    ("Limuru Tea","Agribusiness - Crops & Farming","Kiambu"),("TotalEnergies Kenya","Energy - Oil & Gas","Nairobi"),
    ("KenolKobil","Energy - Oil & Gas","Nairobi"),("Bamburi Cement","Manufacturing - Construction Materials","Mombasa"),
    ("East African Portland Cement","Manufacturing - Construction Materials","Machakos"),("Nation Media Group","Media & Broadcasting","Nairobi"),
    ("Standard Group","Media & Broadcasting","Nairobi"),("Royal Media Services","Media & Broadcasting","Nairobi"),
    ("Nairobi Securities Exchange","Capital Markets & Investment Banks","Nairobi"),("Centum Investment","Capital Markets & Investment Banks","Nairobi"),
    ("TransCentury","Construction & Infrastructure","Nairobi"),("Car & General","Automotive - Dealerships","Nairobi"),
    ("Sameer Africa","Manufacturing - Automotive & Assembly","Nairobi"),("Uchumi Supermarkets","Retail - Supermarkets & Chains","Nairobi"),
    ("Naivas Supermarket","Retail - Supermarkets & Chains","Nairobi"),("Quickmart","Retail - Supermarkets & Chains","Nairobi"),
    ("Carrefour Kenya","Retail - Supermarkets & Chains","Nairobi"),("Brookside Dairy","Agribusiness - Livestock & Dairy","Kiambu"),
    ("New Kenya Co-operative Creameries","Agribusiness - Livestock & Dairy","Nakuru"),("KCC","Agribusiness - Livestock & Dairy","Nairobi"),
    ("Bidco Africa","Manufacturing - Food Processing","Thika"),("Unilever Kenya","FMCG - Personal Care & Household","Nairobi"),
    ("PZ Cussons","FMCG - Personal Care & Household","Nairobi"),("BAT Kenya","Manufacturing - Food Processing","Nairobi"),
    ("Crown Paints","Manufacturing - Chemicals & Plastics","Nairobi"),("Kenya Pipeline","Energy - Oil & Gas","Nairobi"),
    ("Mumias Sugar","Agribusiness - Crops & Farming","Kakamega"),("Nzoia Sugar","Agribusiness - Crops & Farming","Bungoma"),
]

# Real KPIN-style prices - Nyeri + Nairobi + Mombasa baselines, KES
PRICES = [
    ("Maize (90kg bag)", 5200, "Nyeri", "Agriculture"),("Beans (90kg bag)", 10800, "Nyeri", "Agriculture"),
    ("Irish Potatoes (50kg)", 3200, "Nyeri", "Agriculture"),("Cabbages (per piece)", 65, "Nyeri", "Agriculture"),
    ("Tomatoes (crate)", 2800, "Nyeri", "Agriculture"),("Onions (50kg)", 5200, "Nyeri", "Agriculture"),
    ("Milk (litre)", 58, "Nyeri", "Agribusiness - Livestock & Dairy"),("Eggs (tray 30)", 420, "Nyeri", "Agriculture"),
    ("Chicken (broiler, per kg)", 380, "Nyeri", "Agriculture"),("Beef (per kg)", 650, "Nyeri", "Agriculture"),
    ("Maize (90kg bag)", 5400, "Nairobi", "Agriculture"),("Beans (90kg bag)", 11200, "Nairobi", "Agriculture"),
    ("Tomatoes (crate)", 3100, "Nairobi", "Agriculture"),("Milk (litre)", 62, "Nairobi", "Agribusiness - Livestock & Dairy"),
    ("Maize (90kg bag)", 5800, "Mombasa", "Agriculture"),("Rice (50kg)", 6800, "Mombasa", "Agriculture"),
    ("Sugar (50kg)", 6800, "Nairobi", "FMCG - Food & Beverage"),("Cooking Oil (5L)", 1450, "Nairobi", "FMCG - Food & Beverage"),
    ("Bread (400g)", 75, "Nairobi", "FMCG - Food & Beverage"),("Petrol (litre)", 194, "Nairobi", "Energy - Oil & Gas"),
]

def seed_all():
    with Session(engine) as db:
        # Companies
        existing = db.exec(select(func.count()).select_from(Company)).first() or 0
        if existing == 0:
            for name, sector, county in COMPANIES:
                db.add(Company(name=name, sector=sector, county=county, description=f"{name} - {sector} in {county}, Kenya"))
            db.commit()
        # Prices - PriceData + MarketMetric both, so all pages see data
        p_count = db.exec(select(func.count()).select_from(PriceData)).first() or 0
        if p_count == 0:
            for product, price, county, sector in PRICES:
                db.add(PriceData(product_name=product, county=county, sector=sector, price=float(price), tenant_id="public"))
                db.add(MarketMetric(product=product, county=county, sector=sector, company_name="KPIN", avg_price_kes=float(price), demand_score=72.0, user_id=1))
            db.commit()
        # News / Risk - so Risk Sentinel is not empty
        n_count = db.exec(select(func.count()).select_from(NewsArticle)).first() or 0
        if n_count == 0:
            for title, cat, county in [
                ("CBK holds base rate - lending costs stable for SMEs","policy","Nairobi"),
                ("KRA eTIMS deadline - SMEs must onboard","policy","Nairobi"),
                ("Kenya maize prices ease after harvest in Nyeri","market","Nyeri"),
                ("Tea auction prices rise at Mombasa auction","market","Mombasa"),
                ("New export rules for horticulture to EU","policy","Nairobi"),
            ]:
                db.add(NewsArticle(title=title, summary=title, content=title, source="EvidLens", category=cat, county=county))
            db.commit()
        # Social / Consumer Pulse
        s_count = db.exec(select(func.count()).select_from(SocialMention)).first() or 0
        if s_count == 0:
            for content, plat, county, sector in [
                ("Maize prices in Nyeri are fair this week","X","Nyeri","Agriculture"),
                ("Milk prices up in Nairobi","Facebook","Nairobi","Agribusiness - Livestock & Dairy"),
                ("New supermarket opening in Nyeri town","Facebook","Nyeri","Retail - Supermarkets & Chains"),
            ]:
                db.add(SocialMention(platform=plat, content=content, author="Kenya Consumer", sentiment="neutral", county=county, sector=sector))
            db.commit()
        # Export
        e_count = db.exec(select(func.count()).select_from(ExportOpportunity)).first() or 0
        if e_count == 0:
            for prod, dest, county in [("Tea","United Kingdom","Kericho"),("Coffee","Germany","Nyeri"),("Avocado","Netherlands","Murang'a"),("Flowers","Netherlands","Nakuru"),("Macadamia","China","Embu")]:
                db.add(ExportOpportunity(product=prod, destination_country=dest, county=county, description=f"{prod} export to {dest}"))
            db.commit()
        # Knowledge
        k_count = db.exec(select(func.count()).select_from(KnowledgeChunk)).first() or 0
        if k_count == 0:
            for sector in ["Agriculture","Banks","Retail - Supermarkets & Chains","Energy - Oil & Gas"]:
                db.add(KnowledgeChunk(sector=sector, county="Nairobi", chunk_text=f"Kenya {sector} market overview - key players, pricing, regulation.", chunk_type="sector", source="EvidLens"))
            db.commit()
        # Plans + Modules from env if present, else skip - never fail seed
        try:
            from app.core.seed_master_plans import seed_plans_modules
            seed_plans_modules(db)
        except Exception:
            pass
        return {
            "companies": db.exec(select(func.count()).select_from(Company)).first(),
            "prices": db.exec(select(func.count()).select_from(PriceData)).first(),
            "metrics": db.exec(select(func.count()).select_from(MarketMetric)).first(),
            "news": db.exec(select(func.count()).select_from(NewsArticle)).first(),
            "exports": db.exec(select(func.count()).select_from(ExportOpportunity)).first(),
        }

if __name__ == "__main__":
    print(seed_all())
