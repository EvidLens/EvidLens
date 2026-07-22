from sqlmodel import Session
from datetime import datetime, timedelta
from fastapi import Depends
import httpx, asyncio, os

from App.db import get_session
from App.kenyalensiq import services
from App.kenyalensiq.router import router

# ===== CONFIG =====
CONNECTORS = {
    "kra": {"url": "https://api.kra.go.ke/sme-registrations", "key_env": "KRA_KEY", "module": "core"},
    "cbk": {"url": "https://api.centralbank.go.ke/sme-loans", "key_env": "CBK_KEY", "module": "capital"},
    "nbs": {"url": "https://api.knbs.or.ke/business-index", "key_env": "NBS_KEY", "module": "health"},
    "mpesa": {"url": "https://api.safaricom.co.ke/statistics", "key_env": "MPESA_KEY", "module": "money"}, # optional
}

# ===== MAPPING =====
async def map_and_ingest(session: Session, tenant_id: str, source: str, raw: dict):
    """Map external API data to KenyaLensIQ schema and ingest"""
    cfg = CONNECTORS[source]

    payload = {
        "business_id": raw.get("pin") or raw.get("till") or raw.get("id") or raw.get("reg_no"),
        "name": raw.get("business_name") or raw.get("name"),
        "region": raw.get("county") or raw.get("region"),
        "sector": raw.get("sector") or raw.get("industry"),
        "module": cfg["module"],
        "source": source,
        "ingested_at": datetime.utcnow().isoformat(),
        "all_answers": raw
    }
    await services.ingest_live(session, payload, tenant_id, user_id="system", source=source)

async def run_connector(session: Session, tenant_id: str, source: str):
    cfg = CONNECTORS[source]
    api_key = os.getenv(cfg["key_env"])
    if not api_key:
        print(f"[SKIP] {source} - missing {cfg['key_env']}")
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(cfg["url"], headers={"Authorization": f"Bearer {api_key}"})
            res.raise_for_status()
            data = res.json()

            items = data.get("results", data.get("data", [])) # handle diff APIs
            for item in items:
                await map_and_ingest(session, tenant_id, source, item)

        services.log_audit(session, tenant_id, "system", "connector_run", source)
        print(f"[OK] {source}: ingested {len(items)} records")

    except Exception as e:
        print(f"[ERROR] {source}: {e}")
        services.log_audit(session, tenant_id, "system", "connector_error", f"{source}:{str(e)}")

async def auto_ingest_worker(session: Session, tenant_id: str):
    """Runs every 1 hour via cron/celery. Only runs sources in tenant plan"""
    sub = services.get_subscription(session, tenant_id)
    if not sub:
        return

    allowed_modules = sub.modules.split(",")

    for source, cfg in CONNECTORS.items():
        if cfg["module"] in allowed_modules: # Don't pull data for modules they don't pay for
            await run_connector(session, tenant_id, source)

def run_all_connectors(session: Session):
    """Sync wrapper for router. Runs for all active tenants"""
    tenants = services.get_all_active_tenants(session) # you need this in services.py
    for t in tenants:
        asyncio.run(auto_ingest_worker(session, t.id))

    # Also run trial alerts
    services.check_trial_expiry_alerts(session)

# ===== ROUTER ENDPOINT =====
@router.post("/connectors/run")
def run_connectors(session: Session = Depends(get_session)):
    """Call this via cron every hour: 0 * * * * curl -X POST https://api.yourdomain.com/kenyalensiq/connectors/run"""
    run_all_connectors(session)
    return {"status": "ok", "ran_at": datetime.utcnow()}
