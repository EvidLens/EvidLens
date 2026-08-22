import os
import json
from datetime import datetime
from sqlmodel import Session, select, delete, create_engine
from sqlalchemy import text

# Use your existing engine
from app.core.db import engine
from app.core.models import MarketMetric, Company, KnowledgeChunk, ExportOpportunity

# Plans models - your original import was wrong
try:
    from app.core.models import Plan, Module, Sector, AddOn, ALCService
    HAS_PLAN_MODELS = True
except ImportError:
    try:
        from app.modules.core.models import Plan, Module, Sector, AddOn, ALCService
        HAS_PLAN_MODELS = True
    except ImportError:
        HAS_PLAN_MODELS = False
        print("Plan models not found - will skip plans seed")

def load_json(path):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Failed to load {path}: {e}")
    return []

def seed_plans(session):
    if not HAS_PLAN_MODELS:
        return
    
    print("Seeding Plans, Modules, Sectors...")
    try:
        session.exec(delete(ALCService))
        session.exec(delete(AddOn))
        session.exec(delete(Sector))
        session.exec(delete(Module))
        session.exec(delete(Plan))
        session.commit()
    except Exception as e:
        print(f"Delete failed (first run): {e}")
        session.rollback()

    plans = [
        Plan(code="EV-FREE", name="Free Trial", monthly_price=0, annual_price=0, lanes=1, modules=1, users=1, competitors=1, leads_per_quarter=0, support_sla="None", description="14 Days", features=json.dumps(["14 Days Access","1 Lane, 1 Module","1 User","Watermarked Exports"])),
        Plan(code="EV-STARTER", name="Freemium", monthly_price=0, annual_price=0, lanes=1, modules=3, users=1, competitors=3, leads_per_quarter=0, support_sla="Community", description="Forever", features=json.dumps(["Forever Free","1 Lane, 3 Modules","Delayed Data","Watermarked Reports"])),
        Plan(code="EV-SME", name="SME", monthly_price=20000, annual_price=204000, lanes=1, modules=3, users=1, competitors=3, leads_per_quarter=250, support_sla="24hr Email", description="SMEs", features=json.dumps(["1 Lane + 3 Modules","1 User","Track 3 Competitors","1 Quarterly Sector Report","250 B2B Leads per Year","Email Support - 24hr","Kenya-First Data: County Level","Exportable Reports: PDF, Excel"])),
        Plan(code="EV-GROWTH", name="Growth", monthly_price=50000, annual_price=510000, lanes=3, modules=9, users=5, competitors=10, leads_per_quarter=1000, support_sla="4hr WhatsApp", description="Most Popular", features=json.dumps(["3 Lanes + 9 Modules","5 Users","Track 10 Competitors","Monthly Dashboard","1,000 B2B Leads per Year","Bi-Weekly Alerts","WhatsApp Support - 4hr","Access to 9 Lanes of Intelligence"])),
        Plan(code="EV-PRO", name="Professional", monthly_price=100000, annual_price=1020000, lanes=6, modules=15, users=15, competitors=999, leads_per_quarter=4000, support_sla="4hr WhatsApp", description="Large Corporates", features=json.dumps(["6 Lanes + 15 Modules","15 Users","Unlimited Competitors","Bi-Weekly Alerts + Briefings","4,000 B2B Leads per Year","Dedicated Account Manager","FREE Standard Onboarding","Priority Support - 4hr"])),
        Plan(code="EV-ENT", name="Enterprise", monthly_price=200000, annual_price=2040000, lanes=10, modules=19, users=999, competitors=999, leads_per_quarter=9999, support_sla="4hr WhatsApp", description="Govt, Tier 1 Banks", features=json.dumps(["9 Lanes + 19 Modules","Unlimited Users","API Access","Weekly Executive Briefings","2x Custom Research Projects per Year","Dedicated Analyst Team","FREE Enterprise Implementation","99.5% SLA Uptime"])),
    ]
    
    modules = [
        Module(module_number=1,lane="MI",name="Real-Time Market Data Terminal",usage="Live pricing, macro news, CBK rates",how_it_helps="Banks: Risk analysis. Retail: Pricing. Investors: Market sizing",sector_examples="All 75 Sectors",min_plan="EV-SME"),
        Module(module_number=2,lane="CO",name="Private & Public Company Database",usage="Track VC, PE, M&A, valuations",how_it_helps="IB: Due diligence. Lawyers: M&A. SMEs: Partnerships",sector_examples="All 75 Sectors",min_plan="EV-SME"),
        Module(module_number=3,lane="AI",name="AI-Powered Research Search Engine",usage="Search earnings, filings, docs",how_it_helps="Researchers: Cut research 80%. Executives: Plain English answers",sector_examples="All 75 Sectors",min_plan="EV-PRO"),
    ]
    
    sectors_list = ["Banks","Retail - Supermarkets & Chains","FMCG - Food & Beverage","Agribusiness - Crops & Farming","Telcos & ISPs","Real Estate - Developers","Healthcare - Hospitals & Clinics","Education - Universities & Colleges","Logistics & Transport","E-Commerce & Marketplaces","Hospitality - Hotels & Resorts","Energy - Electricity Generation","Agriculture","Fintech","Manufacturing"]
    sectors = [Sector(sector_number=i+1,name=n,parent_category="General") for i,n in enumerate(sectors_list)]

    for item in plans + modules + sectors:
        session.add(item)
    
    print(f"Added {len(plans)} plans, {len(modules)} modules, {len(sectors)} sectors")

def seed_market_data(session):
    print("Seeding Market Data for Price Oracle, Competitive, Demand...")
    
    counties_data = load_json("app/modules/seed_data/kenya_counties.json")
    sectors_data = load_json("app/modules/seed_data/kenya_sectors.json")
    
    county_names = []
    for c in counties_data:
        if isinstance(c, str): county_names.append(c)
        elif isinstance(c, dict): county_names.append(c.get("name") or c.get("county") or "Nairobi")
    if not county_names:
        county_names = ["Nairobi","Mombasa","Kisumu","Nakuru","Uasin Gishu","Kiambu","Machakos","Nyeri","Kisii","Meru","Kilifi","Kwale","Nandi","Kericho","Bungoma"]

    sector_names = []
    for s in sectors_data:
        if isinstance(s, str): sector_names.append(s.lower())
        elif isinstance(s, dict): sector_names.append((s.get("name") or "agriculture").lower())
    if not sector_names:
        sector_names = ["agriculture","retail","fintech","health","education","logistics","energy","manufacturing","hospitality","real estate"]

    # Check if market data already exists
    existing_company = session.exec(select(Company)).first()
    if existing_company:
        print(f"Market data already exists: {existing_company.name} - skipping market seed")
        return

    count = 0
    for sector in sector_names[:8]:
        for county in county_names[:12]:
            company = Company(name=f"{sector.title()} Solutions {county}", sector=sector, county=county, description=f"Leading {sector} company in {county}")
            session.add(company)
            metric = MarketMetric(sector=sector, county=county, metric_type="demand", value=float(60 + count % 40), date=datetime.utcnow())
            session.add(metric)
            price = MarketMetric(sector=sector, county=county, metric_type="price", value=float(120 + count % 180), date=datetime.utcnow())
            session.add(price)
            kb = KnowledgeChunk(title=f"{sector.title()} Policy 2024 - {county}", content=f"Kenya {sector} policy framework for {county} County. Regulations, licenses, compliance.", category="policy", sector=sector)
            session.add(kb)
            export = ExportOpportunity(sector=sector, market="EU", product=f"{sector} products", description=f"Export {sector} to EU from {county}")
            session.add(export)
            count += 1
    
    print(f"Prepared {count} market entries")

def seed_all():
    with Session(engine) as session:
        seed_plans(session)
        seed_market_data(session)
        session.commit()
        print("=== SEED COMPLETE ===")
        print("Plans + Market Data seeded. App is now LIVE for clients.")

if __name__ == "__main__":
    seed_all()
