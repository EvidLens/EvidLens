from sqlmodel import Session
from datetime import datetime
import httpx
import asyncio
import os
from app.modules.database import get_session
from app.modules.kenyalensiq import services

CONNECTORS = {
    "kra": {"url": "https://api.kra.go.ke/sme-registrations", "key_env": "KRA_KEY", "module": "core"},
    "cbk": {"url": "https://api.centralbank.go.ke/sme-loans", "key_env": "CBK_KEY", "module": "capital"},
    "nbs": {"url": "https://api.knbs.or.ke/business-index", "key_env": "NBS_KEY", "module": "health"},
    "mpesa": {"url": "https://api.safaricom.co.ke/statistics", "key_env": "MPESA_KEY", "module": "money"},
}

async def map_and_ingest(session: Session, tenant_id: str, source: str, raw: dict):
    cfg = CONNECTORS[source]
    payload = {
        "business_id": raw.get("pin") or raw.get("till") or raw.get("id") or raw.get("reg_no"),
        "name": raw.get("business_name") or raw.get("name"),
        "region": raw.get("county") or raw.get("region"),
        "county": raw.get("county"),
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
        return
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(cfg["url"], headers={"Authorization": f"Bearer {api_key}"})
            res.raise_for_status()
            data = res.json()
            items = data.get("results", data.get("data", []))
            for item in items:
                await map_and_ingest(session, tenant_id, source, item)
        services.log_audit(session, tenant_id, "system", "connector_run", source, {"source": source})
    except Exception as e:
        services.log_audit(session, tenant_id, "system", "connector_error", source, {"error": str(e)})

async def auto_ingest_worker(session: Session, tenant_id: str):
    sub = services.get_subscription(session, tenant_id)
    if not sub:
        return
    allowed_modules = sub.modules
    for source, cfg in CONNECTORS.items():
        if cfg["module"] in allowed_modules:
            await run_connector(session, tenant_id, source)

def run_all_connectors(session: Session):
    tenants = services.get_all_active_tenants(session)
    for t in tenants:
        asyncio.run(auto_ingest_worker(session, t.tenant_id))
    services.check_trial_expiry_alerts(session)
