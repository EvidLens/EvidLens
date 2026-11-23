import json
import os
import httpx
from sqlalchemy import text
from app.core.db import engine
from app.modules.knowledge_base.models import KENYA_SECTORS
from app.modules.location_intel.models import KENYA_COUNTIES, KENYA_SUBCOUNTIES
def get_list(url, label):
    if not url:
        raise ValueError(f"{label} is not set")
    r = httpx.get(url, timeout=30.0)
    r.raise_for_status()
    d = r.json()
    if isinstance(d, list) and len(d) > 1 and isinstance(d[1], list):
        return d[1]
    if isinstance(d, dict):
        if "results" in d and isinstance(d["results"], dict) and "companies" in d["results"]:
            out = []
            for row in d["results"]["companies"]:
                c = row.get("company", {})
                out.append({"name": c.get("name"), "sector": c.get("industry_code") or "General", "county": c.get("registered_address_in_full") or "Kenya", "description": c.get("company_type") or ""})
            return out
        for k in ["results", "data", "items", "rows"]:
            if k in d and isinstance(d[k], list):
                return d[k]
    if isinstance(d, list):
        return d
    raise ValueError(f"Bad JSON from {label}: {url}")
def get_env_list(name):
    raw = os.environ.get(name, "")
    if not raw:
        raise ValueError(f"{name} is not set")
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"{name} must be a non-empty JSON list")
    return data
def seed_all():
    counties = KENYA_COUNTIES
    sectors = KENYA_SECTORS
    plans_data = get_env_list("SEED_PLANS_JSON")
    modules_data = get_env_list("SEED_MODULES_JSON")
    companies_data = get_list(os.environ.get("SEED_COMPANIES_URL", ""), "SEED_COMPANIES_URL")
    prices_data = get_list(os.environ.get("SEED_PRICES_URL", ""), "SEED_PRICES_URL")
    source_data = get_list(os.environ.get("SEED_SOURCE_URL", ""), "SEED_SOURCE_URL")
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT count(*) FROM company")).scalar() or 0
        if existing > 20:
            print(f"Already seeded: {existing} companies - seeding plans only, market data kept")
            for p in plans_data:
                conn.execute(text("INSERT INTO plan (code, name, monthly_price, annual_price, lanes, modules, users, competitors, leads_per_quarter, support_sla, description, features) VALUES (:code, :name, :mp, :ap, :lanes, :mods, :users, :comps, :leads, :sla, :desc, :features) ON CONFLICT (code) DO NOTHING"), {"code": p["code"], "name": p["name"], "mp": p["monthly_price"], "ap": p["annual_price"], "lanes": p["lanes"], "mods": p["modules"], "users": p["users"], "comps": p["competitors"], "leads": p["leads_per_quarter"], "sla": p["support_sla"], "desc": p["description"], "features": json.dumps(p.get("features", []))})
            conn.commit()
            print(f"Plans seeded: {len(plans_data)}")
            return {"seeded": False, "reason": "already_seeded", "companies": existing}
        print("Seeding Plans...")
        for tbl in ["alcservice", "addon", "module", "plan"]:
            conn.execute(text(f"DELETE FROM {tbl}"))
        conn.commit()
        for p in plans_data:
            conn.execute(text("INSERT INTO plan (code, name, monthly_price, annual_price, lanes, modules, users, competitors, leads_per_quarter, support_sla, description, features) VALUES (:code, :name, :mp, :ap, :lanes, :mods, :users, :comps, :leads, :sla, :desc, :features) ON CONFLICT (code) DO NOTHING"), {"code": p["code"], "name": p["name"], "mp": p["monthly_price"], "ap": p["annual_price"], "lanes": p["lanes"], "mods": p["modules"], "users": p["users"], "comps": p["competitors"], "leads": p["leads_per_quarter"], "sla": p["support_sla"], "desc": p["description"], "features": json.dumps(p.get("features", []))})
        for m in modules_data:
            conn.execute(text("INSERT INTO module (module_number, lane, name, usage, how_it_helps, sector_examples, min_plan) VALUES (:num, :lane, :name, :usage, :helps, :ex, :minp) ON CONFLICT (module_number) DO NOTHING"), {"num": m["module_number"], "lane": m["lane"], "name": m["name"], "usage": m["usage"], "helps": m["how_it_helps"], "ex": m["sector_examples"], "minp": m["min_plan"]})
        conn.commit()
        print(f"Plans seeded: {len(plans_data)}")
        print(f"Modules seeded: {len(modules_data)}")
        for tbl in ["sector", "location_geo", "opportunity_heatmaps", "location_demand", "export_opportunities", "knowledge_chunks", "social_mentions", "news_articles", "price_data", "market_metrics", "company"]:
            conn.execute(text(f"DELETE FROM {tbl}"))
        conn.commit()
        for i, name in enumerate(sectors):
            conn.execute(text("INSERT INTO sector (sector_number, name, parent_category) VALUES (:n, :name, 'General') ON CONFLICT (sector_number) DO NOTHING"), {"n": i + 1, "name": name})
        conn.commit()
        print(f"Sectors: {len(sectors)}")
        geo = 0
        for county in counties:
            conn.execute(text("INSERT INTO location_geo (level, name, parent) VALUES ('county', :name, 'Kenya') ON CONFLICT DO NOTHING"), {"name": county})
            geo += 1
            for sub in KENYA_SUBCOUNTIES.get(county, []):
                conn.execute(text("INSERT INTO location_geo (level, name, parent) VALUES ('sub_county', :name, :parent) ON CONFLICT DO NOTHING"), {"name": sub, "parent": county})
                geo += 1
        conn.commit()
        print(f"Location geo: {geo}")
        count = 0
        for item in companies_data:
            name = item.get("name")
            if not name:
                raise ValueError(f"Company row missing name: {item}")
            conn.execute(text("INSERT INTO company (name, sector, county, description) VALUES (:n, :s, :c, :d) ON CONFLICT DO NOTHING"), {"n": name, "s": item.get("sector") or "General", "c": item.get("county") or "Kenya", "d": item.get("description") or ""})
            count += 1
        conn.commit()
        print(f"Companies seeded: {count}")
        pcount = 0
        for item in prices_data:
            product = item.get("product_name") or item.get("product") or item.get("name") or item.get("indicator", {}).get("value") if isinstance(item.get("indicator"), dict) else item.get("product_name") or item.get("product") or item.get("name")
            val = item.get("price") or item.get("avg_price_kes") or item.get("avg_price") or item.get("value")
            county = item.get("county") or item.get("country", {}).get("value") if isinstance(item.get("country"), dict) else item.get("county") or "Kenya"
            sector = item.get("sector") or "General"
            year = item.get("date") or item.get("year") or ""
            if val is None:
                raise ValueError(f"Price row missing value: {item}")
            label = product or f"Kenya CPI {year}"
            conn.execute(text("INSERT INTO price_data (product_name, product, county, sector, price, avg_price_kes) VALUES (:pn, :p, :c, :s, :pr, :pr) ON CONFLICT DO NOTHING"), {"pn": label, "p": label, "c": county, "s": sector, "pr": val})
            conn.execute(text("INSERT INTO market_metrics (product, county, sector, avg_price_kes, demand_score, timestamp) VALUES (:p, :c, :s, :pr, :d, NOW()) ON CONFLICT DO NOTHING"), {"p": label, "c": county, "s": sector, "pr": val, "d": item.get("demand_score") or 80})
            pcount += 1
        conn.commit()
        print(f"Prices seeded: {pcount}")
        dcount = 0
        for row in source_data:
            sector = row.get("sector") or row.get("category") or "General"
            county = row.get("county") or row.get("country", {}).get("value") if isinstance(row.get("country"), dict) else row.get("county") or "Kenya"
            product = row.get("product_name") or row.get("product") or sector
            title = row.get("title") or f"{sector} in {county}"
            summary = row.get("summary") or ""
            content = row.get("content") or row.get("value") or ""
            if isinstance(content, (int, float)):
                content = str(content)
            source = row.get("source") or "EvidLens"
            conn.execute(text("INSERT INTO news_articles (title, summary, content, source, category, county) VALUES (:t, :su, :co, :src, :cat, :c) ON CONFLICT DO NOTHING"), {"t": title, "su": summary, "co": content, "src": source, "cat": sector, "c": county})
            conn.execute(text("INSERT INTO social_mentions (platform, content, author, sentiment, county, sector) VALUES (:plat, :con, :auth, :sent, :c, :s) ON CONFLICT DO NOTHING"), {"plat": row.get("platform") or "web", "con": row.get("content") or product, "auth": row.get("author") or "EvidLens", "sent": row.get("sentiment") or "neutral", "c": county, "s": sector})
            conn.execute(text("INSERT INTO knowledge_chunks (sector, county, chunk_text, chunk_type, source) VALUES (:s, :c, :txt, :typ, :src) ON CONFLICT DO NOTHING"), {"s": sector, "c": county, "txt": row.get("chunk_text") or content, "typ": row.get("chunk_type") or "policy", "src": source})
            conn.execute(text("INSERT INTO export_opportunities (country, product, opportunity_score) VALUES (:country, :p, :sc) ON CONFLICT DO NOTHING"), {"country": row.get("country") or "Kenya", "p": product, "sc": row.get("opportunity_score") or row.get("value") or 0})
            conn.execute(text("INSERT INTO location_demand (county, product_category, demand_score) VALUES (:c, :p, :d) ON CONFLICT DO NOTHING"), {"c": county, "p": product, "d": row.get("demand_score") or 0})
            conn.execute(text("INSERT INTO opportunity_heatmaps (sector, county, opportunity_score, country) VALUES (:s, :c, :sc, 'Kenya') ON CONFLICT DO NOTHING"), {"s": sector, "c": county, "sc": row.get("opportunity_score") or row.get("value") or 0})
            dcount += 1
        conn.commit()
        print(f"Derived rows seeded: {dcount}")
        print(f"SEED COMPLETE: {count} companies, {pcount} prices, {dcount} derived")
        result = {}
        for tbl in ["company", "market_metrics", "price_data", "sector", "location_geo", "plan", "module", "news_articles", "social_mentions", "knowledge_chunks", "export_opportunities", "location_demand", "opportunity_heatmaps"]:
            c = conn.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
            print(f"{tbl}: {c}")
            result[tbl] = c
        return {"seeded": True, "companies": count, "prices": pcount, "derived": dcount, "counts": result}
if __name__ == "__main__":
    seed_all()
