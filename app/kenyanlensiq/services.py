from sqlmodel import Session, select, func
from typing import Dict, Any, List
from App.kenyalensiq.models import *
from datetime import datetime, timedelta
from fastapi import WebSocket, HTTPException
import httpx

class ConnectionManager:
    def __init__(self): self.active: Dict[str, List[WebSocket]] = {}
    async def connect(self, tenant_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(tenant_id, []).append(ws)
    def disconnect(self, tenant_id: str, ws: WebSocket): self.active[tenant_id].remove(ws)
    async def broadcast(self, tenant_id: str, msg: dict):
        for ws in self.active.get(tenant_id, []): await ws.send_json(msg)
manager = ConnectionManager()

def get_subscription(session: Session, tenant_id: str) -> LensSubscription:
    sub = session.exec(select(LensSubscription).where(LensSubscription.tenant_id == tenant_id)).first()
    if not sub: raise HTTPException(404, "No subscription")
    if datetime.utcnow() > sub.expires_at: raise HTTPException(403, "Subscription expired")
    return sub

def check_module_access(session: Session, tenant_id: str, module: str) -> LensSubscription:
    sub = get_subscription(session, tenant_id)
    if module not in sub.modules: raise HTTPException(403, f"Upgrade to access {module}")
    return sub

def log_audit(session: Session, tenant_id: str, user_id: str, action: str, module: str, payload: dict = {}):
    session.add(LensAudit(tenant_id=tenant_id, user_id=user_id, action=action, module=module, payload=payload))
    session.commit()

async def fire_alert(session: Session, alert: LensAlert, value: Any):
    alert.last_triggered = datetime.utcnow()
    session.add(alert); session.commit()
    if alert.destination.startswith("http"):
        async with httpx.AsyncClient() as client: await client.post(alert.destination, json={"alert": alert.name, "value": value})

async def ingest_live(session: Session, payload: dict, tenant_id: str, user_id: str, source: str = "api"):
    business = session.exec(select(LensBusiness).where(LensBusiness.external_id == payload['business_id'])).first()
    if not business:
        business = LensBusiness(**{k: payload.get(k) for k in ["external_id","name","region","county","sector","size_category","employees_total"]})
        session.add(business); session.commit(); session.refresh(business)
    else:
        business.updated_at = datetime.utcnow(); session.add(business)

    survey = LensSurvey(business_id=business.id, source=source, data=payload.get('all_answers', {}))
    session.add(survey); session.commit()
    log_audit(session, tenant_id, user_id, "ingest_data", "core", {"business_id": business.id})

    alerts = session.exec(select(LensAlert).where(LensAlert.tenant_id == tenant_id, LensAlert.is_active == True)).all()
    for alert in alerts:
        cond = alert.condition
        if business.region == cond.get("region") and survey.data.get(cond.get("metric")) == cond.get("value"):
            await fire_alert(session, alert, survey.data.get(cond.get("metric")))

    await manager.broadcast(tenant_id, {"event": "new_data", "module": payload.get("module"), "ts": datetime.utcnow().isoformat()})

def query_aggregate(session: Session, tenant_id: str, module: str, json_key: str):
    sub = check_module_access(session, tenant_id, module)
    stmt = select(LensSurvey.data[json_key].astext, func.count()).join(LensBusiness)
    if sub.regions: stmt = stmt.where(LensBusiness.region.in_(sub.regions))
    if sub.sectors: stmt = stmt.where(LensBusiness.sector.in_(sub.sectors))
    stmt = stmt.where(LensSurvey.collected_at > datetime.utcnow() - timedelta(days=90))
    return [{"label": k, "value": c} for k, c in session.exec(stmt.group_by(LensSurvey.data[json_key].astext)).all() if k]
def get_subscription(session: Session, tenant_id: str) -> LensSubscription | None:
    sub = session.exec(select(LensSubscription).where(LensSubscription.tenant_id == tenant_id)).first()
    
    # If no sub, check if they already used trial
    if not sub:
        used_trial = session.exec(select(LensAudit).where(LensAudit.tenant_id == tenant_id, LensAudit.action == "trial_start")).first()
        if used_trial:
            return None # trial already used
        
    # If sub exists but expired, check if within 7 day trial
    if sub and sub.expires_at < datetime.utcnow():
        if sub.plan == "Trial":
            return None # trial expired
    
    return sub

def start_trial(session: Session, tenant_id: str):
    sub = LensSubscription(
        tenant_id=tenant_id,
        plan="Trial",
        modules="core,health", # Starter modules only
        regions="Nairobi",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    session.add(sub)
    log_audit(session, tenant_id, "system", "trial_start", "kenyalensiq")
    session.commit()
    return sub
