from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, Header, BackgroundTasks, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from typing import Dict, Any
from datetime import datetime, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
import io
import csv

from app.modules.kenyalensiq.mpesa import stk_push
from app.models import get_session, LensSubscription, LensAlert, LensMember, LensApiUsage
from app.modules.kenyalensiq import services
from app.modules.kenyalensiq import connectors

router = APIRouter()

templates = Jinja2Templates(directory="app/modules/kenyalensiq/templates")
limiter = Limiter(key_func=lambda req: req.query_params.get("api_key", get_remote_address(req)))

def get_tenant(authorization: str = Header(...)) -> str:
    return authorization.split(" ")[1]

def get_tenant_api(x_api_key: str = Header(...), session: Session = Depends(get_session)) -> str:
    sub = session.exec(select(LensSubscription).where(LensSubscription.api_key == x_api_key)).first()
    if not sub:
        raise HTTPException(401, "Invalid API Key")
    return sub.tenant_id

def require_active_subscription(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    sub = services.get_subscription(session, tenant_id)
    if not sub or datetime.utcnow() > sub.expires_at:
        raise HTTPException(402, "Subscription required")
    return sub

@router.post("/billing/mpesa/stk")
def mpesa_stk(tenant_id: str, amount: int, phone: str):
    res = stk_push(phone, amount, tenant_id)
    return res

@router.post("/webhooks/mpesa")
async def mpesa_callback(req: Request, session: Session = Depends(get_session)):
    body = await req.json()
    callback = body.get("Body", {}).get("stkCallback", {})
    if callback.get("ResultCode")!= 0:
        return {"ResultCode": 0}
    items = {i["Name"]: i["Value"] for i in callback["CallbackMetadata"]["Item"]}
    tenant_id = str(items["AccountReference"])
    receipt = items["MpesaReceiptNumber"]
    exists = session.exec(
        select(LensSubscription).where(LensSubscription.metadata.contains({"last_payment": receipt}))
    ).first()
    if exists:
        return {"ResultCode": 0, "ResultDesc": "Already processed"}
    sub = session.exec(select(LensSubscription).where(LensSubscription.tenant_id == tenant_id)).first()
    if not sub:
        sub = LensSubscription(tenant_id=tenant_id)
    amount = items["Amount"]
    sub.plan = "Pro" if amount == 5000 else "Enterprise"
    sub.modules = ["core", "health", "money", "brand", "demand", "behavior", "policy", "capital", "trade"]
    sub.expires_at = datetime.utcnow() + timedelta(days=30)
    sub.metadata["last_payment"] = receipt
    sub.metadata["last_phone"] = items["PhoneNumber"]
    session.add(sub)
    session.commit()
    return {"ResultCode": 0, "ResultDesc": "Success"}

@router.post("/webhooks/payment")
async def payment_webhook(req: Request, session: Session = Depends(get_session)):
    payload = await req.json()
    if payload.get("payment_status") == "Completed":
        tenant_id = payload.get("merchant_reference")
        sub = services.get_subscription(session, tenant_id) or LensSubscription(tenant_id=tenant_id)
        sub.plan = "Pro"
        sub.modules = ["core", "health", "money", "brand", "demand", "behavior", "policy", "capital", "trade"]
        sub.expires_at = datetime.utcnow() + timedelta(days=30)
        session.add(sub)
        session.commit()
    return {"status": "ok"}

@router.websocket("/ws")
async def ws(websocket: WebSocket, tenant_id: str, session: Session = Depends(get_session)):
    await services.manager.connect(tenant_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        services.manager.disconnect(tenant_id, websocket)

@router.post("/ingest")
async def ingest(
    payload: Dict,
    bg: BackgroundTasks,
    tenant_id: str = Depends(get_tenant),
    user_id: str = Depends(get_tenant),
    session: Session = Depends(get_session)
):
    bg.add_task(services.ingest_live, session, payload, tenant_id, user_id)
    return {"status": "accepted"}

@router.post("/alerts")
def create_alert(alert: LensAlert, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    services.check_module_access(session, tenant_id, "policy")
    alert.tenant_id = tenant_id
    session.add(alert)
    session.commit()
    return alert

@router.get("/export/{module}")
def export(module: str, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    services.check_module_access(session, tenant_id, module)
    data = services.query_aggregate(session, tenant_id, module, "sector")
    stream = io.StringIO()
    csv.writer(stream).writerows([["label", "value"]] + [(d["label"], d["value"]) for d in data])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")

@router.get("/core")
def core(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    services.log_audit(session, sub.tenant_id, sub.tenant_id, "view", "core")
    return services.query_aggregate(session, sub.tenant_id, "core", "sector")

@router.get("/health")
def health(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "health", "performance_last_year")

@router.get("/money")
def money(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "money", "payment_methods_used")

@router.get("/brand")
def brand(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "brand", "brand_awareness")

@router.get("/demand")
def demand(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "demand", "has_health_cover")

@router.get("/behavior")
def behavior(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "behavior", "channel_usage")

@router.get("/policy")
def policy(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "policy", "top_challenges")

@router.get("/capital")
def capital(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "capital", "funding_need")

@router.get("/trade")
def trade(sub: LensSubscription = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.tenant_id, "trade", "geographic_scope")

@router.get("/api/{module}")
def api(module: str, tenant_id: str = Depends(get_tenant_api), session: Session = Depends(get_session)):
    return services.query_aggregate(session, tenant_id, module, "sector")

@router.post("/connectors/run")
async def run_connectors(bg: BackgroundTasks, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    bg.add_task(connectors.auto_ingest_worker, session, tenant_id)
    return {"status": "connectors started"}

@router.post("/trial/start")
def start_trial(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    existing = services.get_subscription(session, tenant_id)
    if existing:
        raise HTTPException(400, "You already have a subscription")
    new_sub = services.start_trial(session, tenant_id)
    return {"status": "trial_started", "expires_at": new_sub.expires_at}

@router.get("/me")
def me(sub: LensSubscription = Depends(require_active_subscription)):
    days_left = (sub.expires_at - datetime.utcnow()).days
    return {
        "plan": sub.plan,
        "modules": sub.modules,
        "regions": sub.regions,
        "expires_at": sub.expires_at,
        "days_left": days_left,
        "is_trial": sub.plan == "Trial"
    }

@router.get("/admin/stats")
def admin_stats(session: Session = Depends(get_session)):
    total_subs = session.exec(select(func.count()).select_from(LensSubscription)).first()
    trial_subs = session.exec(select(func.count()).select_from(LensSubscription).where(LensSubscription.plan == "Trial")).first()
    paid_subs = session.exec(select(func.count()).select_from(LensSubscription).where(LensSubscription.plan!= "Trial")).first()
    mrr = paid_subs * 5000
    return {"total_subs": total_subs, "trial_subs": trial_subs, "paid_subs": paid_subs, "mrr": mrr}

@router.post("/admin/grant")
def grant_access(tenant_id: str, plan: str, session: Session = Depends(get_session)):
    sub = services.get_subscription(session, tenant_id)
    if not sub:
        sub = LensSubscription(tenant_id=tenant_id)
    if plan == "Pro":
        sub.plan = "Pro"
        sub.modules = ["core", "health", "money", "brand", "demand", "behavior", "policy", "capital", "trade"]
        sub.expires_at = datetime.utcnow() + timedelta(days=30)
    elif plan == "Enterprise":
        sub.plan = "Enterprise"
        sub.modules = ["core", "health", "money", "brand", "demand", "behavior", "policy", "capital", "trade"]
        sub.expires_at = datetime.utcnow() + timedelta(days=365)
    session.add(sub)
    services.log_audit(session, tenant_id, "admin", "grant_plan", "kenyalensiq", {"plan": plan})
    session.commit()
    return {"status": "granted", "tenant_id": tenant_id, "plan": plan}

@router.get("/team")
def get_team(tenant_id: str, session: Session = Depends(get_session)):
    return session.exec(select(LensMember).where(LensMember.tenant_id == tenant_id)).all()

@router.post("/team/invite")
def invite_member(tenant_id: str, email: str, role: str, user_id: str, session: Session = Depends(get_session)):
    member = LensMember(tenant_id=tenant_id, email=email, role=role, invited_by=user_id, user_id="pending")
    session.add(member)
    session.commit()
    return {"status": "invited"}

@router.delete("/team/{member_id}")
def remove_member(member_id: int, session: Session = Depends(get_session)):
    member = session.get(LensMember, member_id)
    session.delete(member)
    session.commit()
    return {"status": "removed"}

@router.post("/report/build")
def build_report(tenant_id: str, payload: dict, session: Session = Depends(get_session)):
    services.check_module_access(session, tenant_id, payload["module"])
    data = services.query_aggregate(session, tenant_id, payload["module"], payload["metric"])
    return {"data": data, "filters": payload.get("filters", {})}

@router.get("/report/export/{report_id}")
def export_report(report_id: str):
    return Response(content="csv_data", media_type="text/csv")

@router.get("/embed/{module}")
@limiter.limit("100/hour")
def embed_widget(module: str, request: Request, api_key: str, session: Session = Depends(get_session)):
    sub = session.exec(select(LensSubscription).where(LensSubscription.api_key == api_key)).first()
    if not sub:
        return templates.TemplateResponse("embed_locked.html", {"request": request, "reason": "Invalid API Key"})
    if datetime.utcnow() > sub.expires_at or sub.plan == "Trial":
        return templates.TemplateResponse("embed_locked.html", {"request": request, "reason": "Upgrade Required"})
    if module not in sub.modules:
        return templates.TemplateResponse("embed_locked.html", {"request": request, "reason": f"Upgrade to unlock {module}"})
    session.add(LensApiUsage(api_key=api_key, endpoint=module))
    session.commit()
    data = services.query_aggregate(session, sub.tenant_id, module, "sector")
    branding = sub.metadata or {}
    return templates.TemplateResponse("embed.html", {"request": request, "data": data, "branding": branding})
