from sqlmodel import Session
from App.kenyalensiq.services import ingest_live
from datetime import datetime
import httpx, asyncio

CONNECTORS = {
    "kra": {"url": "https://api.kra.go.ke/sme-registrations", "key": "KRA_KEY"},
    "mpesa": {"url": "https://api.safaricom.co.ke/statistics", "key": "MPESA_KEY"},
    "cbk": {"url": "https://api.centralbank.go.ke/sme-loans", "key": "CBK_KEY"},
    "nbs": {"url": "https://api.knbs.or.ke/business-index", "key": "NBS_KEY"},
}

async def map_and_ingest(session: Session, tenant_id: str, source: str, raw: dict):
    """Map external API data to our schema and ingest"""
    payload = {
        "business_id": raw.get("pin") or raw.get("till") or raw.get("id"),
        "name": raw.get("business_name"),
        "region": raw.get("county"),
        "sector": raw.get("sector"),
        "module": source,
        "all_answers": raw
    }
    await ingest_live(session, payload, tenant_id, user_id="system", source=source)

async def run_connector(session: Session, tenant_id: str, source: str):
    cfg = CONNECTORS[source]
    async with httpx.AsyncClient() as client:
        res = await client.get(cfg["url"], headers={"Authorization": f"Bearer {cfg['key']}"})
        data = res.json()
        for item in data.get("results", []):
            await map_and_ingest(session, tenant_id, source, item)

async def auto_ingest_worker(session: Session, tenant_id: str):
    """Runs every 1 hour via cron/celery"""
    for source in ["kra", "cbk", "nbs"]: # APIs you have access to
        await run_connector(session, tenant_id, source)
@router.post("/connectors/run")
def run_connectors(session: Session = Depends(get_session)):
    # existing data pulls
    run_all_connectors(session) 
    
    # new: trial alerts
    services.check_trial_expiry_alerts(session)
    
    return {"status": "ok"}
