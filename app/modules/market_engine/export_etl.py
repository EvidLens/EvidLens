# ETL: UN Comtrade -> Postgres trade_flows
# Run: python -m app.modules.market_engine.export_etl
# Or Render Cron: python -m app.modules.market_engine.export_etl
import os, time, sys
import httpx
from sqlmodel import Session, select, delete
from app.modules.database import engine, get_session
from app.modules.market_engine.export_models import TradeFlow, ProductCatalogue
from app.modules.market_engine.export_navigator import HS_CATALOGUE, COUNTRY_CODES, DISTANCE_KM, TARIFFS

COMTRADE_KEY = os.getenv("COMTRADE_KEY", "")
URL = "https://comtradeapi.un.org/data/v1/get/C/A/HS"

def fetch_one(hs: str, year: int, flow: str = "X"):
    """Kenya (404) exports for one HS, all partners. Returns list of dicts."""
    if not COMTRADE_KEY:
        print("No COMTRADE_KEY - using curated seed only")
        return []
    with httpx.Client(timeout=60) as c:
        r = c.get(URL, params={"reporterCode": "404", "period": str(year), "flowCode": flow, "partnerCode": "0", "cmdCode": hs}, headers={"Ocp-Apim-Subscription-Key": COMTRADE_KEY})
        if r.status_code != 200:
            print(f"Comtrade {hs} {year} -> {r.status_code} {r.text[:200]}")
            return []
        return r.json().get("data", [])

def seed_catalogue(session: Session):
    for hs, (name, counties, cat) in HS_CATALOGUE.items():
        if not session.get(ProductCatalogue, hs):
            session.add(ProductCatalogue(hs=hs, name=name, hs4=hs[:4], counties=counties, category=cat))
    session.commit()

def run_etl(years=(2023, 2024), limit_hs=None):
    hs_list = list(HS_CATALOGUE.keys())
    if limit_hs: hs_list = hs_list[:limit_hs]
    with Session(engine) as session:
        seed_catalogue(session)
        for hs in hs_list:
            name, counties, cat = HS_CATALOGUE[hs]
            for year in years:
                # Delete old for this hs/year so re-run is idempotent
                session.exec(delete(TradeFlow).where(TradeFlow.hs == hs, TradeFlow.year == year, TradeFlow.flow == "X"))
                session.commit()
                rows = fetch_one(hs, year, "X")
                if not rows:
                    # Curated seed for top products so DB is never empty without key
                    if hs in ("090230","090111","080440","060319","080261"):
                        from app.modules.market_engine.export_navigator import SEED_FLOWS
                        for s in SEED_FLOWS.get(hs, []):
                            session.add(TradeFlow(hs=hs, product=name, partner=s["destination"], partner_code=COUNTRY_CODES.get(s["destination"],0), year=year, flow="X", value_usd=s["value"]*1_000_000, growth_pct=s["growth"], kenya_share_pct=s["kenya_share"], tariff_pct=s["tariff"], distance_km=s["distance"], counties=s["county"], source="Curated / KEPROBA / KNBS"))
                    continue
                # Need previous year for growth - fetch inside loop is slow, so growth calc from stored 2023 vs 2024 in second pass
                for row in rows:
                    partner = row.get("partnerDesc", "")
                    if partner in ("World", "Kenya"): continue
                    val = float(row.get("primaryValue") or 0)
                    qty = float(row.get("netWgt") or 0)
                    session.add(TradeFlow(hs=hs, product=name, partner=partner, partner_code=int(row.get("partnerCode") or 0), year=year, flow="X", value_usd=val, qty_kg=qty, unit_value=(val/qty if qty else 0), distance_km=DISTANCE_KM.get(partner, 7000), tariff_pct=TARIFFS.get(partner, 0), counties=counties, source="UN Comtrade", updated_at=time.strftime("%Y-%m-%d")))
                session.commit()
                print(f"OK {hs} {name} {year} -> {len(rows)} partners")
                time.sleep(0.6)  # respect Comtrade rate limit
        # Second pass: growth = (2024-2023)/2023, share = Kenya / world imports (approx from value)
        print("ETL done")

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_etl(limit_hs=limit)
