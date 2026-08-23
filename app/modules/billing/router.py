from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.core.db import get_session
from app.core.billing import PLAN_MODULES, PLAN_PRICE, PLAN_DAYS
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/billing", tags=["billing-page"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def billing_page(request: Request, current_user = Depends(get_current_user), db: Session = Depends(get_session)):
    plans_list = []
    for name in ["Trial", "Starter", "Growth", "Pro", "Enterprise"]:
        plans_list.append({
            "name": name,
            "price": PLAN_PRICE.get(name, 0),
            "credits": len(PLAN_MODULES.get(name, [])) * 10,
            "modules": PLAN_MODULES.get(name, []),
            "days": PLAN_DAYS.get(name, 30)
        })
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "current_user": current_user,
        "plans": plans_list
    })
