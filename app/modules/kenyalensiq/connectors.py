from sqlmodel import Session
from datetime import datetime, timezone
import httpx
import asyncio
import os
import json
from app.core.db import get_session
from app.modules.kenyalensiq import services

UTC = timezone.utc

CONNECTORS = {
    "kra": {"url": "https://api.kra.go.ke/sme-registrations", "key_env": "KRA_KEY", "module": "core"},
    "cbk": {"url": "https://api.centralbank.go.ke/sme-loans", "key_env": "CBK_KEY", "module": "capital"},
    "nbs": {"url": "https://api.knbs.or.ke/business-index", "key_env": "NBS_KEY", "module": "health"},
    "mpesa": {"url": "https://api.safaricom.co.ke/statistics", "key_env": "MPESA_KEY", "module": "money"},
}

async def map_and_ingest(session: Session, user_id: int, source: str, raw: dict):
    cfg = CONNECTORS[source]
    payload = {
        "business_id": raw.get("pin") or raw.get("till") or raw.get("id") or raw.get("reg_no"),
        "name": raw.get("business_name") or raw.get("name"),
        "region": raw.get("county") or raw.get("region"),
        "county": raw.get("county"),
        "sector": raw.get("sector") or raw.get("industry"),
        "module": cfg["module"],
        "source": source,
        "ingested_at": datetime.now(UTC).isoformat(),
        "all_answers": raw
    }
    await services.ingest_live(session, payload, str(user_id), str(user_id), source=source)

async def run_connector(session: Session, user_id: int, source: str):
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
                await map_and_ingest(session, user_id, source, item)
        services.log_audit(session, user_id, user_id, "connector_run", source, {"source": source})
    except Exception as e:
        services.log_audit(session, user_id, user_id, "connector_error", source, {"error": str(e)})

async def auto_ingest_worker(session: Session, user_id: int):
    sub = services.get_subscription(session, user_id)
    if not sub:
        return
    allowed_modules = json.loads(sub.features_json or '[]')
    for source, cfg in CONNECTORS.items():
        if cfg["module"] in allowed_modules:
            await run_connector(session, user_id, source)

def run_all_connectors(session: Session):
    tenants = services.get_all_active_tenants(session)
    for t in tenants:
        asyncio.run(auto_ingest_worker(session, t.id))
    services.check_trial_expiry_alerts(session)
