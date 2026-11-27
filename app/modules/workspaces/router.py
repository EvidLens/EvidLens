from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from typing import Optional
import logging
from app.core.db import get_session as get_db
from app.core.guards import get_current_user
from app.core.models import User
router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("evidlens.workspaces")
try:
    from app.core.models import Workspace, WorkspaceMember
    HAS_MODEL = True
except Exception:
    HAS_MODEL = False
    Workspace = None
    WorkspaceMember = None
try:
    from app.modules.auth.models import AuthUser
    HAS_AUTH_USER = True
except Exception:
    HAS_AUTH_USER = False
    AuthUser = None

def _ws_to_dict(ws, members_count=0, members=None):
    return {
        "id": getattr(ws, "id", 0),
        "name": getattr(ws, "name", "Workspace"),
        "plan": getattr(ws, "plan", "Free"),
        "credits": getattr(ws, "credits", 0),
        "members": members or [],
        "member_count": members_count,
    }

def _resolve_user_id(request, current_user):
    if current_user is not None:
        uid = getattr(current_user, "id", None)
        if uid is not None:
            return uid, getattr(current_user, "email", None)
    try:
        uid = request.session.get("user_id")
        if uid is not None:
            return int(uid), request.session.get("email")
    except Exception:
        pass
    try:
        uid = request.cookies.get("user_id")
        if uid is not None:
            return int(uid), None
    except Exception:
        pass
    return None, None

def _get_real_user(db, request, current_user):
    user_id, email = _resolve_user_id(request, current_user)
    if email is None and current_user is not None:
        email = getattr(current_user, "email", None)
    if HAS_AUTH_USER and AuthUser is not None:
        try:
            if user_id is not None:
                real = db.get(AuthUser, user_id)
                if real:
                    return real
        except Exception:
            pass
        try:
            if email:
                rows = db.exec(select(AuthUser).where(AuthUser.email == email)).all()
                if rows:
                    return rows[0]
        except Exception:
            pass
    try:
        if user_id is not None:
            real = db.get(User, user_id)
            if real:
                return real
    except Exception:
        pass
    try:
        if email:
            rows = db.exec(select(User).where(User.email == email)).all()
            if rows:
                return rows[0]
    except Exception:
        pass
    return None

def _is_json_request(request):
    accept = (request.headers.get("accept", "") or "").lower()
    ctype = (request.headers.get("content-type", "") or "").lower()
    return "application/json" in accept or "application/json" in ctype

async def _get_name(request, form_name):
    if form_name:
        return (form_name or "").strip()
    try:
        ctype = (request.headers.get("content-type", "") or "").lower()
        if "application/json" in ctype:
            body = await request.json()
            if isinstance(body, dict):
                return str(body.get("name", "") or "").strip()
    except Exception:
        pass
    try:
        form = await request.form()
        return str(form.get("name", "") or "").strip()
    except Exception:
        pass
    return ""

def _unauthorized(request):
    if _is_json_request(request):
        return JSONResponse({"ok": False, "error": "Session expired. Please logout and login again."}, status_code=401)
    return RedirectResponse("/login?next=/workspaces", status_code=303)

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def list_workspaces(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workspaces = []
    current_workspace_id = None
    real_user = _get_real_user(db, request, current_user)
    try:
        if HAS_MODEL and real_user:
            rows = db.exec(select(Workspace).where(Workspace.owner_id == real_user.id)).all()
            for ws in rows:
                members = []
                try:
                    mrows = db.exec(select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)).all()
                    members = [{"full_name": getattr(m, "full_name", None) or getattr(m, "name", None) or getattr(m, "email", "User"), "email": getattr(m, "email", "")} for m in mrows]
                except Exception:
                    members = [{"full_name": getattr(real_user, "full_name", None) or getattr(real_user, "email", "You"), "email": getattr(real_user, "email", "")}]
                workspaces.append(_ws_to_dict(ws, len(members), members))
            if workspaces:
                current_workspace_id = workspaces[0]["id"]
                try:
                    current_workspace_id = getattr(real_user, "current_workspace_id", None) or current_workspace_id
                except Exception:
                    pass
    except Exception as e:
        logger.exception(f"list_workspaces failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    return templates.TemplateResponse("workspaces.html", {
        "request": request, "current_user": current_user, "user": current_user,
        "workspaces": workspaces, "current_workspace_id": current_workspace_id,
    })

@router.post("/create")
async def create_workspace(request: Request, name: Optional[str] = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = await _get_name(request, name)
    is_json = _is_json_request(request)
    real_user = _get_real_user(db, request, current_user)
    if not real_user:
        try:
            db.rollback()
        except Exception:
            pass
        if is_json:
            return JSONResponse({"ok": False, "error": "Session expired. Please logout and login again."}, status_code=401)
        return RedirectResponse("/login?next=/workspaces", status_code=303)
    if not name:
        if is_json:
            return JSONResponse({"ok": False, "error": "Workspace name is required"}, status_code=400)
        return RedirectResponse("/workspaces?error=Name+required", status_code=303)
    if len(name) > 80:
        name = name[:80]
    try:
        if not HAS_MODEL:
            raise RuntimeError("Workspace model not found in app.core.models")
        ws = Workspace(name=name, owner_id=real_user.id, plan="Free", credits=0)
        db.add(ws)
        db.commit()
        db.refresh(ws)
        try:
            db.add(WorkspaceMember(workspace_id=ws.id, user_id=real_user.id, role="owner", full_name=getattr(real_user, "full_name", None), email=getattr(real_user, "email", "")))
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        try:
            real_user.current_workspace_id = ws.id
            db.add(real_user)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    except Exception as e:
        logger.exception(f"create_workspace failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        if is_json:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
        return RedirectResponse("/workspaces?error=Create+failed", status_code=303)
    if is_json:
        return JSONResponse({"ok": True, "workspace": {"id": ws.id, "name": ws.name}})
    return RedirectResponse("/workspaces", status_code=303)

@router.post("/switch")
async def switch_workspace(request: Request, workspace_id: Optional[int] = Form(None), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_json = _is_json_request(request)
    if workspace_id is None:
        try:
            ctype = (request.headers.get("content-type", "") or "").lower()
            if "application/json" in ctype:
                body = await request.json()
                if isinstance(body, dict):
                    workspace_id = body.get("workspace_id") or body.get("id")
                    if workspace_id is not None:
                        workspace_id = int(workspace_id)
        except Exception:
            pass
    if workspace_id is None:
        return JSONResponse({"ok": False, "error": "Workspace id is required"}, status_code=400) if is_json else RedirectResponse("/workspaces?error=Id+required", status_code=303)
    real_user = _get_real_user(db, request, current_user)
    if not real_user:
        return JSONResponse({"ok": False, "error": "Session expired. Please logout and login again."}, status_code=401) if is_json else RedirectResponse("/login?next=/workspaces", status_code=303)
    try:
        if HAS_MODEL:
            ws = db.get(Workspace, workspace_id)
            if not ws:
                raise ValueError("Workspace not found")
            if getattr(ws, "owner_id", None) != real_user.id:
                raise ValueError("Workspace not found")
            try:
                real_user.current_workspace_id = workspace_id
                db.add(real_user)
                db.commit()
            except Exception:
                pass
    except Exception as e:
        logger.exception(f"switch failed: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400) if is_json else RedirectResponse("/workspaces?error=Switch+failed", status_code=303)
    return JSONResponse({"ok": True, "workspace_id": workspace_id}) if is_json else RedirectResponse("/workspaces", status_code=303)

@router.get("/{workspace_id}", response_class=HTMLResponse)
async def workspace_detail(request: Request, workspace_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ws = None
    members = []
    real_user = _get_real_user(db, request, current_user)
    if HAS_MODEL and real_user:
        try:
            ws = db.get(Workspace, workspace_id)
            if ws and getattr(ws, "owner_id", None) != real_user.id:
                ws = None
            if ws:
                mrows = db.exec(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)).all()
                members = [{"full_name": getattr(m, "full_name", None) or getattr(m, "email", "User"), "email": getattr(m, "email", "")} for m in mrows]
        except Exception:
            pass
    if not ws:
        return RedirectResponse("/workspaces?error=Not+found", status_code=303)
    return templates.TemplateResponse("workspaces.html", {
        "request": request, "current_user": current_user, "user": current_user,
        "workspaces": [_ws_to_dict(ws, len(members), members)],
        "current_workspace_id": workspace_id,
    })
