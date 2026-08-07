from app.core.models import KenyaLensApiUsage
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from slowapi import Limiter
from slowapi.util import get_remote_address
import io
import csv
import json

from app.core.db import get_session
from app.modules.kenyalensiq.mpesa import stk_push
from app.modules.kenyalensiq import services
from app.modules.kenyalensiq import connectors

UTC = timezone.utc
router = APIRouter()
templates = Jinja2Templates(directory="app/modules/kenyalensiq/templates")
limiter = Limiter(key_func=lambda req: req.query_params.get("api_key", get_remote_address(req)))

def _to_old_format(sub):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    if not sub: return None
    return {
        "tenant_id": str(sub.user_id),
        "plan": sub.plan_code.replace("EV-", ""),
        "modules": json.loads(sub.features_json or '[]'),
        "regions": [],
        "expires_at": sub.renews_at,
        "extra_data": json.loads(sub.metadata_json or '{}')
    }

def get_tenant(authorization: str = Header(...)) -> str:
    return authorization.split(" ")[1]

def get_tenant_api(x_api_key: str = Header(...), session: Session = Depends(get_session)) -> str:
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    sub = session.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.api_key == x_api_key)).first()
    if not sub:
        raise HTTPException(401, "Invalid API Key")
    return str(sub.user_id)

def require_active_subscription(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    sub = services.get_subscription(session, int(tenant_id))
    if not sub or datetime.now(UTC) > sub.renews_at or sub.status!= "active":
        raise HTTPException(402, "Subscription required")
    return sub

@router.post("/billing/mpesa/stk")
def mpesa_stk(tenant_id: str, amount: int, phone: str):
    res = stk_push(phone, amount, tenant_id)
    return res

@router.post("/webhooks/mpesa")
async def mpesa_callback(req: Request, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    body = await req.json()
    callback = body.get("Body", {}).get("stkCallback", {})
    if callback.get("ResultCode")!= 0:
        return {"ResultCode": 0}
    items = {i["Name"]: i["Value"] for i in callback["CallbackMetadata"]["Item"]}
    user_id = int(items["AccountReference"])
    receipt = items["MpesaReceiptNumber"]
    metadata = json.loads(sub.metadata_json or '{}') if (sub := session.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.user_id == user_id)).first()) else {}
    if metadata.get("last_payment") == receipt:
        return {"ResultCode": 0, "ResultDesc": "Already processed"}
    sub = sub or KenyaLensSubscription(user_id=user_id)
    amount = items["Amount"]
    sub.plan_code = "EV-PRO" if amount == 5000 else "EV-ENT"
    sub.status = "active"
    sub.renews_at = datetime.now(UTC) + timedelta(days=30)
    sub.api_credits = 1000 if amount == 5000 else 5000
    sub.lead_credits = 250 if amount == 5000 else 1000
    metadata["last_payment"] = receipt
    metadata["last_phone"] = items["PhoneNumber"]
    sub.metadata_json = json.dumps(metadata)
    session.add(sub)
    session.commit()
    return {"ResultCode": 0, "ResultDesc": "Success"}

@router.post("/webhooks/payment")
async def payment_webhook(req: Request, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    payload = await req.json()
    if payload.get("payment_status") == "Completed":
        user_id = int(payload.get("merchant_reference"))
        sub = services.get_subscription(session, user_id) or KenyaLensSubscription(user_id=user_id)
        sub.plan_code = "EV-PRO"
        sub.status = "active"
        sub.renews_at = datetime.now(UTC) + timedelta(days=30)
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
async def ingest(payload: Dict, bg: BackgroundTasks, tenant_id: str = Depends(get_tenant), user_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    bg.add_task(services.ingest_live, session, payload, tenant_id, user_id)
    return {"status": "accepted"}

@router.post("/alerts")
def create_alert(alert, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensAlert
    services.check_module_access(session, int(tenant_id), "policy")
    alert.user_id = int(tenant_id)
    session.add(alert)
    session.commit()
    return alert

@router.get("/export/{module}")
def export(module: str, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    services.check_module_access(session, int(tenant_id), module)
    data = services.query_aggregate(session, int(tenant_id), module, "sector")
    stream = io.StringIO()
    csv.writer(stream).writerows([["label", "value"]] + [(d["label"], d["value"]) for d in data])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")

@router.get("/core")
def core(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    services.log_audit(session, sub.user_id, sub.user_id, "view", "core")
    return services.query_aggregate(session, sub.user_id, "core", "sector")

@router.get("/health")
def health(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "health", "performance_last_year")

@router.get("/money")
def money(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "money", "payment_methods_used")

@router.get("/brand")
def brand(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "brand", "brand_awareness")

@router.get("/demand")
def demand(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "demand", "has_health_cover")

@router.get("/behavior")
def behavior(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "behavior", "channel_usage")

@router.get("/policy")
def policy(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "policy", "top_challenges")

@router.get("/capital")
def capital(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "capital", "funding_need")

@router.get("/trade")
def trade(sub = Depends(require_active_subscription), session: Session = Depends(get_session)):
    return services.query_aggregate(session, sub.user_id, "trade", "geographic_scope")

@router.get("/api/{module}")
def api(module: str, tenant_id: str = Depends(get_tenant_api), session: Session = Depends(get_session)):
    return services.query_aggregate(session, int(tenant_id), module, "sector")

@router.post("/connectors/run")
async def run_connectors(bg: BackgroundTasks, tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    bg.add_task(connectors.auto_ingest_worker, session, tenant_id)
    return {"status": "connectors started"}

@router.post("/trial/start")
def start_trial(tenant_id: str = Depends(get_tenant), session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    existing = services.get_subscription(session, int(tenant_id))
    if existing:
        raise HTTPException(400, "You already have a subscription")
    new_sub = KenyaLensSubscription(
        user_id=int(tenant_id), plan_code="EV-FREE", status="active",
        renews_at=datetime.now(UTC) + timedelta(days=14), api_credits=10
    )
    session.add(new_sub)
    session.commit()
    return {"status": "trial_started", "expires_at": new_sub.renews_at}

@router.get("/me")
def me(sub = Depends(require_active_subscription)):
    days_left = (sub.renews_at - datetime.now(UTC)).days
    old = _to_old_format(sub)
    return {
        "plan": old["plan"], "modules": old["modules"], "regions": old["regions"],
        "expires_at": old["expires_at"], "days_left": days_left, "is_trial": sub.plan_code == "EV-FREE"
    }

@router.get("/admin/stats")
def admin_stats(session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    total_subs = session.exec(select(func.count()).select_from(KenyaLensSubscription)).first()
    trial_subs = session.exec(select(func.count()).select_from(KenyaLensSubscription).where(KenyaLensSubscription.plan_code == "EV-FREE")).first()
    paid_subs = session.exec(select(func.count()).select_from(KenyaLensSubscription).where(KenyaLensSubscription.plan_code!= "EV-FREE")).first()
    mrr = paid_subs * 50000
    return {"total_subs": total_subs, "trial_subs": trial_subs, "paid_subs": paid_subs, "mrr": mrr}

@router.post("/admin/grant")
def grant_access(tenant_id: str, plan: str, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription
    sub = services.get_subscription(session, int(tenant_id))
    if not sub:
        sub = KenyaLensSubscription(user_id=int(tenant_id))
    plan_map = {"Pro": "EV-PRO", "Enterprise": "EV-ENT"}
    sub.plan_code = plan_map.get(plan, "EV-PRO")
    sub.status = "active"
    sub.renews_at = datetime.now(UTC) + timedelta(days=30 if plan == "Pro" else 365)
    sub.features_json = json.dumps(["core", "health", "money", "brand", "demand", "behavior", "policy", "capital", "trade"])
    session.add(sub)
    services.log_audit(session, int(tenant_id), "admin", "grant_plan", "kenyalensiq", {"plan": plan})
    session.commit()
    return {"status": "granted", "tenant_id": tenant_id, "plan": plan}

@router.get("/team")
def get_team(tenant_id: str, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensMember
    return session.exec(select(KenyaLensMember).where(KenyaLensMember.user_id == int(tenant_id))).all()

@router.post("/team/invite")
def invite_member(tenant_id: str, email: str, role: str, user_id: str, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensMember
    member = KenyaLensMember(user_id=int(tenant_id), email=email, role=role)
    session.add(member)
    session.commit()
    return {"status": "invited"}

@router.delete("/team/{member_id}")
def remove_member(member_id: int, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensMember
    member = session.get(KenyaLensMember, member_id)
    session.delete(member)
    session.commit()
    return {"status": "removed"}

@router.post("/report/build")
def build_report(tenant_id: str, payload: dict, session: Session = Depends(get_session)):
    services.check_module_access(session, int(tenant_id), payload["module"])
    data = services.query_aggregate(session, int(tenant_id), payload["module"], payload["metric"])
    return {"data": data, "filters": payload.get("filters", {})}

@router.get("/report/export/{report_id}")
def export_report(report_id: str):
    return Response(content="csv_data", media_type="text/csv")

@router.get("/embed/{module}")
@limiter.limit("100/hour")
def embed_widget(module: str, request: Request, api_key: str, session: Session = Depends(get_session)):
    from app.modules.kenyalensiq.models import KenyaLensSubscription, KenyaLensApiUsage
    sub = session.exec(select(KenyaLensSubscription).where(KenyaLensSubscription.api_key == api_key)).first()
    if not sub:
        return templates.TemplateResponse("embed_locked.html", {"request": request, "reason": "Invalid API Key"})
    if datetime.now(UTC) > sub.renews_at or sub.plan_code == "EV-FREE":
        return templates.TemplateResponse("embed_locked.html", {"request": request, "reason": "Upgrade Required"})
    modules = json.loads(sub.features_json or '[]')
    if module not in modules:
        return templates.TemplateResponse("embed_locked.html", {"request": request, "reason": f"Upgrade to unlock {module}"})
    session.add(KenyaLensApiUsage(user_id=sub.user_id, endpoint=module))
    session.commit()
    data = services.query_aggregate(session, sub.user_id, module, "sector")
    branding = json.loads(sub.metadata_json or '{}')
    return templates.TemplateResponse("embed.html", {"request": request, "data": data, "branding": branding})
