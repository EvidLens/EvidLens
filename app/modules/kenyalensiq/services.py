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
    sub = session.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.tenant_id == tenant_id)).first()
    if not sub:
        used_trial = session.exec(select(KenyaLensAudit).where(KenyaLensAudit.tenant_id == tenant_id, KenyaLensAudit.action == "trial_start")).first()
        if used_trial:
            return None
    if sub and sub.expires_at < datetime.utcnow():
        if sub.plan == "Trial":
            return None
    return sub

def require_active_subscription(session: Session, tenant_id: str) -> KenyaLensSubscription:
    sub = get_subscription(session, tenant_id)
    if not sub:
        raise HTTPException(403, "Subscription required")
    if datetime.utcnow() > sub.expires_at:
        raise HTTPException(403, "Subscription expired")
    return sub

def check_module_access(session: Session, tenant_id: str, module: str) -> KenyaLensSubscription:
    sub = require_active_subscription(session, tenant_id)
    if module not in sub.modules:
        raise HTTPException(403, f"Upgrade to access {module}")
    return sub

def log_audit(session: Session, tenant_id: str, user_id: str, action: str, module: str, payload: dict = {}):
    session.add(KenyaLensAudit(tenant_id=tenant_id, user_id=user_id, action=action, module=module, payload=payload))
    session.commit()

def get_all_active_tenants(session: Session):
    return session.exec(select(KenyaLensTenant).where(KenyaLensTenant.is_active == True)).all()

def get_tenant_user(session: Session, tenant_id: str):
    return session.exec(select(KenyaLensUser).where(KenyaLensUser.tenant_id == tenant_id, KenyaLensUser.is_admin == True)).first()

def create_alert(session: Session, data: dict):
    session.add(KenyaLensAlert(**data))
    session.commit()

async def fire_alert(session: Session, alert: KenyaLensAlert, value: Any):
    alert.last_triggered = datetime.utcnow()
    session.add(alert)
    session.commit()
    if alert.destination and alert.destination.startswith("http"):
        async with httpx.AsyncClient() as client:
            await client.post(alert.destination, json={"alert": alert.name, "value": value})

async def ingest_live(session: Session, payload: dict, tenant_id: str, user_id: str, source: str = "api"):
    business = session.exec(select(KenyaLensBusiness).where(KenyaLensBusiness.external_id == payload['business_id'])).first()
    if not business:
        business = KenyaLensBusiness(**{k: payload.get(k) for k in ["external_id","name","region","county","sector","size_category","employees_total"]})
        session.add(business)
        session.commit()
        session.refresh(business)
    else:
        business.updated_at = datetime.utcnow()
        session.add(business)

    survey = KenyaLensSurvey(business_id=business.id, source=source, module=payload.get("module", "core"), data=payload.get('all_answers', {}))
    session.add(survey)
    session.commit()
    log_audit(session, tenant_id, user_id, "ingest_data", "core", {"business_id": business.id})

    alerts = session.exec(select(KenyaLensAlert).where(KenyaLensAlert.tenant_id == tenant_id, KenyaLensAlert.is_active == True)).all()
    for alert in alerts:
        cond = alert.condition or {}
        if business.region == cond.get("region") and survey.data.get(cond.get("metric")) == cond.get("value"):
            await fire_alert(session, alert, survey.data.get(cond.get("metric")))

    await manager.broadcast(tenant_id, {"event": "new_data", "module": payload.get("module"), "ts": datetime.utcnow().isoformat()})

def query_aggregate(session: Session, tenant_id: str, module: str, json_key: str):
    sub = check_module_access(session, tenant_id, module)
    stmt = select(KenyaLensSurvey.data[json_key].astext, func.count()).join(KenyaLensBusiness)

    if sub.regions:
        stmt = stmt.where(KenyaLensBusiness.region.in_(sub.regions))
    if sub.sectors:
        stmt = stmt.where(KenyaLensBusiness.sector.in_(sub.sectors))

    stmt = stmt.where(KenyaLensSurvey.module == module)
    stmt = stmt.where(KenyaLensSurvey.collected_at > datetime.utcnow() - timedelta(days=90))

    total = session.exec(select(func.count()).select_from(KenyaLensSurvey).join(KenyaLensBusiness)).first()
    rows = session.exec(stmt.group_by(KenyaLensSurvey.data[json_key].astext)).all()

    return {
        "count": total,
        "by_sector": [{"name": k, "count": c} for k, c in rows if k]
    }

def start_trial(session: Session, tenant_id: str):
    sub = KenyaLensSubscription(
        tenant_id=tenant_id,
        plan="Trial",
        modules=["core","health"],
        regions=["Nairobi"],
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    session.add(sub)
    log_audit(session, tenant_id, "system", "trial_start", "kenyalensiq")
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
        already_alerted = session.exec(
            select(KenyaLensAudit).where(
                KenyaLensAudit.tenant_id == sub.tenant_id,
                KenyaLensAudit.action == "trial_24h_alert_sent"
            )
        ).first()
        if already_alerted:
            continue

        days_left = (sub.expires_at - datetime.utcnow()).days
        create_alert(session, {
            "tenant_id": sub.tenant_id,
            "name": "trial_expiring",
            "type": "trial_expiring",
            "title": "Trial expires tomorrow",
            "message": f"Your KenyaLensIQ 7-day trial ends in {days_left} day. Upgrade to keep access.",
            "link": "/billing/checkout?product=kenyalensiq&plan=Pro"
        })

        user = get_tenant_user(session, sub.tenant_id)
        if user:
            send_email(
                to=user.email,
                subject="Your KenyaLensIQ Trial Ends in 24 Hours",
                body=f"Hi {user.name}, Your KenyaLensIQ free trial ends tomorrow. Upgrade now: /billing/checkout?product=kenyalensiq&plan=Pro"
            )
        log_audit(session, sub.tenant_id, "system", "trial_24h_alert_sent", "kenyalensiq")

def start_paid_plan(session: Session, tenant_id: str, plan: str):
    sub = get_subscription(session, tenant_id) or KenyaLensSubscription(tenant_id=tenant_id)
    sub.plan = plan
    sub.modules = ["core","health","money","brand","demand","behavior","policy","capital","trade"]
    sub.expires_at = datetime.utcnow() + timedelta(days=30 if plan == "Pro" else 365)
    session.add(sub)
    log_audit(session, tenant_id, "admin", "grant_plan", "kenyalensiq", {"plan": plan})
    session.commit()
    return sub
