from sqlmodel import Session, select, func
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from app.core.models import KenyaLensSubscription
# NEW - IMPORT ALL 4
from app.modules.kenyalensiq.models import (
    KenyaLensSubscription, 
    KenyaLensAlert, 
    KenyaLensMember, 
    KenyaLensApiUsage
)
from fastapi import WebSocket, HTTPException
import httpx
import json

UTC = timezone.utc

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

def _get_user_id(tenant_id: str) -> int:
    return int(tenant_id)

def get_subscription(session: Session, user_id: int) -> KenyaLensSubscription | None:
    sub = session.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == user_id)).first()
    if sub and sub.renews_at and sub.renews_at < datetime.now(UTC):
        if sub.plan_code == "EV-FREE":
            return None
    return sub

def require_active_subscription(session: Session, user_id: int) -> KenyaLensSubscription:
    sub = get_subscription(session, user_id)
    if not sub:
        raise HTTPException(403, "Subscription required")
    if sub.renews_at and datetime.now(UTC) > sub.renews_at:
        raise HTTPException(403, "Subscription expired")
    return sub

def check_module_access(session: Session, user_id: int, module: str) -> KenyaLensSubscription:
    sub = require_active_subscription(session, user_id)
    modules = json.loads(sub.features_json or '[]')
    if modules and module not in modules:
        raise HTTPException(403, f"Module {module} not in plan")
    return sub

def log_audit(session: Session, user_id: int, actor_id: int, action: str, module: str, payload: dict = {}):
    pass # TODO: implement with AuditLog table

def get_all_active_tenants(session: Session):
    return session.exec(select(KenyaLensBusiness)).all()

def get_tenant_user(session: Session, user_id: int):
    return session.exec(select(KenyaLensMember).where(KenyaLensMember.user_id == user_id)).first()

def create_alert(session: Session, data: dict):
    data['user_id'] = int(data.pop('tenant_id', 0))
    session.add(KenyaLensAlert(**data))
    session.commit()

async def fire_alert(session: Session, alert: KenyaLensAlert, value: Any):
    alert.created_at = datetime.now(UTC)
    session.add(alert)
    session.commit()
    if hasattr(alert, 'destination') and alert.destination and alert.destination.startswith("http"):
        async with httpx.AsyncClient() as client:
            await client.post(alert.destination, json={"alert": alert.title, "value": value})

async def ingest_live(session: Session, payload: dict, tenant_id: str, user_id: str, source: str = "api"):
    user_id_int = _get_user_id(user_id)
    business = session.exec(select(KenyaLensBusiness).where(KenyaLensBusiness.id == payload.get('business_id'))).first()
    if not business:
        business = KenyaLensBusiness(
            name=payload.get("name"),
            sector=payload.get("sector"),
            county=payload.get("county")
        )
        session.add(business)
        session.commit()
        session.refresh(business)

    survey = KenyaLensSurvey(user_id=user_id_int, title=payload.get("title","survey"), status="completed")
    session.add(survey)
    session.commit()

    await manager.broadcast(tenant_id, {"event": "new_data", "module": payload.get("module"), "ts": datetime.now(UTC).isoformat()})

def query_aggregate(session: Session, user_id: int, module: str, json_key: str):
    check_module_access(session, user_id, module)
    if module == "core":
        rows = session.exec(
            select(KenyaLensBusiness.sector, func.count(KenyaLensBusiness.id))
           .group_by(KenyaLensBusiness.sector)
        ).all()
    elif module == "money":
        rows = session.exec(
            select(MarketMetric.sector, func.avg(MarketMetric.price))
           .group_by(MarketMetric.sector)
        ).all()
    elif module == "demand":
        rows = session.exec(
            select(MarketMetric.county, func.sum(MarketMetric.demand_score))
           .group_by(MarketMetric.county)
        ).all()
    else:
        rows = session.exec(
            select(KenyaLensBusiness.county, func.count(KenyaLensBusiness.id))
           .group_by(KenyaLensBusiness.county)
        ).all()
    return [{"label": r[0], "value": float(r[1] or 0)} for r in rows]

def start_trial(session: Session, user_id: int):
    sub = KenyaLensSubscription(
        user_id=user_id,
        plan_code="EV-FREE",
        status="active",
        renews_at=datetime.now(UTC) + timedelta(days=7),
        api_credits=10
    )
    session.add(sub)
    session.commit()
    return sub

def check_trial_expiry_alerts(session: Session):
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    expiring_trials = session.exec(
        select(KenyaLensSubscription)
       .where(KenyaLensSubscription.plan_code == "EV-FREE")
       .where(KenyaLensSubscription.renews_at <= tomorrow)
       .where(KenyaLensSubscription.renews_at > datetime.now(UTC))
    ).all()

    for sub in expiring_trials:
        create_alert(session, {
            "tenant_id": str(sub.user_id),
            "title": "Trial expires tomorrow",
            "description": f"Your EvidLens 7-day trial ends soon. Upgrade to keep access.",
            "module": "kenyalensiq",
            "severity": "warning"
        })

def start_paid_plan(session: Session, user_id: int, plan: str):
    sub = get_subscription(session, user_id) or KenyaLensSubscription(user_id=user_id)
    plan_map = {"Pro": "EV-PRO", "Enterprise": "EV-ENT"}
    sub.plan_code = plan_map.get(plan, "EV-PRO")
    sub.status = "active"
    sub.renews_at = datetime.now(UTC) + timedelta(days=30 if plan == "Pro" else 365)
    session.add(sub)
    session.commit()
    return sub
