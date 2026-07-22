from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Header, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from typing import Dict, Any
from app.core.database import get_session
from App.kenyalensiq import services
from App.kenyalensiq.models import LensAlert, LensSubscription
import io, csv

router = APIRouter()

def get_tenant(authorization: str = Header(...)) -> str:
    return authorization.split(" ")[1] # REPLACE WITH YOUR JWT DECODE

def get_tenant_api(x_api_key: str = Header(...), session: Session = Depends(get_session)) -> str:
    sub = session.exec(select(LensSubscription).where(LensSubscription.api_key == x_api_key)).first()
    if not sub: raise HTTPException(401, "Invalid API Key")
    return sub.tenant_id

@router.websocket("/ws")
async def ws(websocket: WebSocket, tenant_id: str, session: Session = Depends(get_session)):
    await services.manager.connect(tenant_id, websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: services.manager.disconnect(tenant_id, websocket)

@router.post("/ingest")
async def ingest(payload: Dict, bg: BackgroundTasks, tenant_id: str = Depends(get_tenant), user_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    bg.add_task(services.ingest_live, session, payload, tenant_id, user_id)
    return {"status": "accepted"}

@router.post("/alerts")
def create_alert(alert: LensAlert, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    services.check_module_access(session, tenant_id, "policy")
    alert.tenant_id = tenant_id
    session.add(alert); session.commit()
    return alert

@router.get("/export/{module}")
def export(module: str, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    services.check_module_access(session, tenant_id, module)
    data = services.query_aggregate(session, tenant_id, module, "sector")
    stream = io.StringIO()
    csv.writer(stream).writerows([["label","value"]] + [(d["label"], d["value"]) for d in data])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")

@router.get("/core")
def core(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    services.log_audit(session, tenant_id, tenant_id, "view", "core")
    return services.query_aggregate(session, tenant_id, "core", "sector")
@router.get("/health")
def health(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "health", "performance_last_year")
@router.get("/money")
def money(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "money", "payment_methods_used")
@router.get("/brand")
def brand(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "brand", "brand_awareness")
@router.get("/demand")
def demand(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "demand", "has_health_cover")
@router.get("/behavior")
def behavior(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "behavior", "channel_usage")
@router.get("/policy")
def policy(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "policy", "top_challenges")
@router.get("/capital")
def capital(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "capital", "funding_need")
@router.get("/trade")
def trade(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, "trade", "geographic_scope")

@router.get("/api/{module}")
def api(module: str, tenant_id: str = Depends(get_tenant_api), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, module, "sector")

from fastapi import BackgroundTasks
from App.kenyalensiq import connectors

@router.post("/connectors/run")
async def run_connectors(bg: BackgroundTasks, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    """Hit this with cron every 1 hour. Or use Celery Beat"""
    bg.add_task(connectors.auto_ingest_worker, session, tenant_id)
    return {"status": "connectors started"}
def require_active_subscription(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    sub = services.get_subscription(session, tenant_id) # already exists in services.py
    return sub

@router.get("/core")
def core(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    services.log_audit(session, sub.tenant_id, sub.tenant_id, "view", "core")
    return services.query_aggregate(session, sub.tenant_id, "core", "sector")
from datetime import datetime, timedelta

@router.post("/trial/start")
def start_trial(sub: LensSubscription = Depends(get_tenant), session: Session = Depends(get_session)):
    existing = services.get_subscription(session, sub)
    if existing:
        raise HTTPException(400, "You already have a subscription")
    new_sub = services.start_trial(session, sub)
    return {"status": "trial_started", "expires_at": new_sub.expires_at}
from datetime import datetime

@router.get("/me")
def me(sub: LensSubscription = Depends(require_active_subscription)):
    days_left = (sub.expires_at - datetime.utcnow()).days
    return {
        "plan": sub.plan, 
        "modules": sub.modules.split(","), 
        "regions": sub.regions.split(","),
        "expires_at": sub.expires_at,
        "days_left": days_left,
        "is_trial": sub.plan == "Trial"
    }
