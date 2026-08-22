from sqlalchemy import text
from app.core.db import engine
from app.modules.knowledge_base.models import KENYA_SECTORS
from app.modules.location_intel.models import KENYA_COUNTIES, KENYA_SUBCOUNTIES

def seed_all():
    counties = KENYA_COUNTIES
    sectors = KENYA_SECTORS

    with engine.connect() as conn:
        try:
            existing = conn.execute(text("SELECT count(*) FROM company")).scalar()
            if existing and existing > 20:
                print(f"Already seeded: {existing} companies - skipping market seed but seeding plans")
            else:
                existing = 0
        except:
            existing = 0

        print("Seeding Plans...")
        for tbl in ["alcservice","addon","module","plan"]:
            try:
                conn.execute(text(f"DELETE FROM {tbl}"))
            except:
                pass
        conn.commit()

        plans_data = [
            ("EV-FREE", "Free Trial", 0, 0, 1, 1, 1, 1, 0, "None", "7 Days"),
            ("EV-STARTER", "Freemium", 0, 0, 1, 3, 1, 3, 0, "Community", "Forever"),
            ("EV-SME", "SME", 20000, 204000, 1, 3, 1, 3, 250, "24hr Email", "SMEs"),
            ("EV-GROWTH", "Growth", 50000, 510000, 3, 9, 5, 10, 1000, "4hr WhatsApp", "Most Popular"),
            ("EV-PRO", "Professional", 100000, 1020000, 6, 15, 15, 999, 4000, "4hr WhatsApp", "Large Corporates"),
            ("EV-ENT", "Enterprise", 200000, 2040000, 10, 19, 999, 999, 9999, "4hr WhatsApp", "Govt, Tier 1 Banks"),
        ]
        for code, name, mp, ap, lanes, mods, users, comps, leads, sla, desc in plans_data:
            conn.execute(text("""
                INSERT INTO plan (code, name, monthly_price, annual_price, lanes, modules, users, competitors, leads_per_quarter, support_sla, description, features)
                VALUES (:code, :name, :mp, :ap, :lanes, :mods, :users, :comps, :leads, :sla, :desc, '[]')
                ON CONFLICT (code) DO NOTHING
            """), {"code": code, "name": name, "mp": mp, "ap": ap, "lanes": lanes, "mods": mods, "users": users, "comps": comps, "leads": leads, "sla": sla, "desc": desc})

        modules_data = [
            (1, "MI", "Real-Time Market Data Terminal", "Live pricing, macro news, CBK rates", "Banks: Risk analysis", "All 75 Sectors", "EV-SME"),
            (2, "CO", "Private & Public Company Database", "Track VC, PE, M&A", "IB: Due diligence", "All 75 Sectors", "EV-SME"),
            (3, "AI", "AI-Powered Research Search Engine", "Search earnings, filings", "Researchers: Cut research 80%", "All 75 Sectors", "EV-PRO"),
        ]
        for num, lane, name, usage, helps, examples, min_plan in modules_data:
            conn.execute(text("""
                INSERT INTO module (module_number, lane, name, usage, how_it_helps, sector_examples, min_plan)
                VALUES (:num, :lane, :name, :usage, :helps, :ex, :minp)
                ON CONFLICT DO NOTHING
            """), {"num": num, "lane": lane, "name": name, "usage": usage, "helps": helps, "ex": examples, "minp": min_plan})
        conn.commit()
        print(f"Plans seeded: {len(plans_data)}")

        for tbl in ["sector","location_geo","opportunity_heatmaps","location_demand","export_opportunities","knowledge_chunks","social_mentions","news_articles","price_data","market_metrics","company"]:
            if existing > 20 and tbl not in ["sector","location_geo"]:
                continue
            try:
                conn.execute(text(f"DELETE FROM {tbl}"))
            except:
                pass
        conn.commit()

        for i, name in enumerate(sectors):
            try:
                conn.execute(text("INSERT INTO sector (sector_number, name, parent_category) VALUES (:n, :name, 'General')"), {"n": i+1, "name": name})
            except:
                conn.execute(text("INSERT INTO sector (id, name) VALUES (:n, :name) ON CONFLICT DO NOTHING"), {"n": i+1, "name": name})
        conn.commit()
        print(f"Sectors: {len(sectors)}")

        geo = 0
        for county in counties:
            conn.execute(text("INSERT INTO location_geo (level, name, parent) VALUES ('county', :name, 'Kenya')"), {"name": county})
            geo += 1
            for sub in KENYA_SUBCOUNTIES.get(county, []):
                conn.execute(text("INSERT INTO location_geo (level, name, parent) VALUES ('sub_county', :name, :parent)"), {"name": sub, "parent": county})
                geo += 1
        conn.commit()
        print(f"Location geo: {geo}")

        if existing > 20:
            print("Market data already exists - done")
            return

        count = 0
        for sector in sectors[:30]:
            for county in counties[:20]:
                conn.execute(text("INSERT INTO company (name, sector, county, description) VALUES (:n, :s, :c, :d)"),
                    {"n": f"{sector} - {county} Ltd", "s": sector, "c": county, "d": f"Leading {sector} in {county}"})
                conn.execute(text("INSERT INTO market_metrics (product, county, sector, avg_price_kes, demand_score, timestamp) VALUES (:p, :c, :s, :pr, :d, NOW())"),
                    {"p": sector, "c": county, "s": sector, "pr": 120 + count % 180, "d": 60 + count % 40})
                conn.execute(text("INSERT INTO price_data (product_name, product, county, sector, price, avg_price_kes) VALUES (:pn, :p, :c, :s, :pr, :pr)"),
                    {"pn": sector, "p": sector, "c": county, "s": sector, "pr": 120 + count % 180})
                conn.execute(text("INSERT INTO news_articles (title, summary, content, source, category, county) VALUES (:t, :su, :co, 'EvidLens', :cat, :c)"),
                    {"t": f"{sector} growth in {county}", "su": f"{sector} update", "co": f"{sector} policy", "cat": sector, "c": county})
                conn.execute(text("INSERT INTO social_mentions (platform, content, author, sentiment, county, sector) VALUES ('twitter', :con, 'EvidLens', 'positive', :c, :s)"),
                    {"con": f"{sector} trending in {county}", "c": county, "s": sector})
                conn.execute(text("INSERT INTO knowledge_chunks (sector, county, chunk_text, chunk_type, source) VALUES (:s, :c, :txt, 'policy', 'EvidLens')"),
                    {"s": sector, "c": county, "txt": f"Kenya {sector} policy for {county}"})
                conn.execute(text("INSERT INTO export_opportunities (country, product, opportunity_score) VALUES ('EU', :p, :sc)"),
                    {"p": sector, "sc": 70 + count % 30})
                conn.execute(text("INSERT INTO location_demand (county, product_category, demand_score) VALUES (:c, :p, :d)"),
                    {"c": county, "p": sector, "d": 60 + count % 40})
                conn.execute(text("INSERT INTO opportunity_heatmaps (sector, county, opportunity_score, country) VALUES (:s, :c, :sc, 'Kenya')"),
                    {"s": sector, "c": county, "sc": 70 + count % 30})
                count += 1
        conn.commit()
        print(f"=== SEED COMPLETE: {count} market entries ===")
        for tbl in ["company","market_metrics","price_data","sector","location_geo","plan"]:
            c = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
            print(f"{tbl}: {c}")

if __name__ == "__main__":
    seed_all()
