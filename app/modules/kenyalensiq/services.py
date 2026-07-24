from sqlmodel import Session, select, func
from typing import Dict, Any, List
from app.modules.kenyalensiq.models import *
from datetime import datetime, timedelta
from fastapi import WebSocket, HTTPException
import httpx

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, tenant_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(tenant_id, []).append(ws)

    def disconnect(self, tenant_id: str, ws: WebSocket):
        if tenant_id in self.active and ws in self.active[tenant_id]:
            self.active[tenant_id].remove(ws)

    async def broadcast(self, tenant_id: str, msg: dict):
        for ws in self.active.get(tenant_id, []):
            await ws.send_json(msg)

manager = ConnectionManager()

def get_subscription(session: Session, tenant_id: str) -> KenyaLensSubscription | None:
    sub = session.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == int(tenant_id))).first()
    if sub and sub.expires_at and sub.expires_at < datetime.utcnow():
        if sub.plan == "Trial":
            return None
    return sub

def require_active_subscription(session: Session, tenant_id: str) -> KenyaLensSubscription:
    sub = get_subscription(session, tenant_id)
    if not sub:
        raise HTTPException(403, "Subscription required")
    if sub.expires_at and datetime.utcnow() > sub.expires_at:
        raise HTTPException(403, "Subscription expired")
    return sub

def check_module_access(session: Session, tenant_id: str, module: str) -> KenyaLensSubscription:
    sub = require_active_subscription(session, tenant_id)
    return sub

def log_audit(session: Session, tenant_id: str, user_id: str, action: str, module: str, payload: dict = {}):
    pass

def get_all_active_tenants(session: Session):
    return session.exec(select(KenyaTenant)).all()

def get_tenant_user(session: Session, tenant_id: str):
    return session.exec(select(KenyaLensMember).where(KenyaLensMember.tenant_id == tenant_id)).first()

def create_alert(session: Session, data: dict):
    session.add(KenyaLensAlert(**data))
    session.commit()

async def fire_alert(session: Session, alert: KenyaLensAlert, value: Any):
    alert.created_at = datetime.utcnow()
    session.add(alert)
    session.commit()
    if hasattr(alert, 'destination') and alert.destination and alert.destination.startswith("http"):
        async with httpx.AsyncClient() as client:
            await client.post(alert.destination, json={"alert": alert.title, "value": value})

async def ingest_live(session: Session, payload: dict, tenant_id: str, user_id: str, source: str = "api"):
    business = session.exec(select(KenyaLensBusiness).where(KenyaLensBusiness.id == payload['business_id'])).first()
    if not business:
        business = KenyaLensBusiness(**{k: payload.get(k) for k in ["tenant_id","name","sector","county"]})
        session.add(business)
        session.commit()
        session.refresh(business)

    survey = KenyaLensSurvey(business_id=business.id, title=payload.get("title","survey"), status="completed")
    session.add(survey)
    session.commit()

    await manager.broadcast(tenant_id, {"event": "new_data", "module": payload.get("module"), "ts": datetime.utcnow().isoformat()})

def query_aggregate(session: Session, tenant_id: str, module: str, json_key: str):
    sub = check_module_access(session, tenant_id, module)
    total = session.exec(select(func.count()).select_from(KenyaLensSurvey)).first()
    return {"count": total, "by_sector": []}

def start_trial(session: Session, tenant_id: str):
    sub = KenyaLensSubscription(
        user_id=int(tenant_id),
        plan="Trial",
        status="active",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    session.add(sub)
    session.commit()
    return sub

def check_trial_expiry_alerts(session: Session):
    tomorrow = datetime.utcnow() + timedelta(days=1)
    expiring_trials = session.exec(
        select(KenyaLensSubscription)
   .where(KenyaLensSubscription.plan == "Trial")
   .where(KenyaLensSubscription.expires_at <= tomorrow)
   .where(KenyaLensSubscription.expires_at > datetime.utcnow())
    ).all()

    for sub in expiring_trials:
        create_alert(session, {
            "tenant_id": str(sub.user_id),
            "title": "Trial expires tomorrow",
            "description": f"Your KenyaLensIQ 7-day trial ends soon. Upgrade to keep access.",
            "module": "kenyalensiq",
            "severity": "warning"
        })

def start_paid_plan(session: Session, tenant_id: str, plan: str):
    sub = get_subscription(session, tenant_id) or KenyaLensSubscription(user_id=int(tenant_id))
    sub.plan = plan
    sub.status = "active"
    sub.expires_at = datetime.utcnow() + timedelta(days=30 if plan == "Pro" else 365)
    session.add(sub)
    session.commit()
    return sub
