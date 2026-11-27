from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
import logging
from .service import create_business, get_business, add_product, create_invoice, add_employee, mark_invoice_paid
from .models import Business, Product, Invoice, Employee
from app.core.db import get_session
from app.core.guards import require_module, consume_credits
from app.modules.auth.dependencies import get_current_user
from app.core.models import Funder, ExportOpportunity
from .scraper import scrape_funding, scrape_exports

router = APIRouter(prefix="/os", tags=["Business OS"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("evidlens.business_os")

class BusinessCreate(BaseModel):
    name: str
    sector: str
    county: str

class ProductCreate(BaseModel):
    business_id: int
    name: str
    sku: str
    selling_price: float
    buying_price: float = 0.0
    stock_qty: int = 0

class InvoiceCreate(BaseModel):
    business_id: int
    customer_name: str
    customer_phone: str
    total_amount: float

class EmployeeCreate(BaseModel):
    business_id: int
    full_name: str
    phone: str
    role: str
    salary_kes: float

class PayInvoice(BaseModel):
    invoice_id: int
    mpesa_receipt: str

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, sector: Optional[str] = Query(None), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None
    stmt = select(Funder)
    if sector:
        stmt = stmt.where((Funder.sector.contains(sector)) | (Funder.sector == "All Sectors"))
    if county:
        stmt = stmt.where((Funder.county.contains(county)) | (Funder.county == "All Counties"))
    rows = list(db.exec(stmt).all())
    funders = []
    for r in rows:
        if r.min_amount is not None and r.max_amount is not None:
            amount = f"KES {int(r.min_amount):,} - {int(r.max_amount):,}"
        elif r.min_amount is not None:
            amount = f"KES {int(r.min_amount):,}+"
        else:
            amount = None
        rate = f"{r.interest_rate}% p.a." if r.interest_rate is not None else None
        funders.append({"name": r.name, "funder_name": r.name, "type": r.type, "funder_type": r.type, "amount": amount, "amount_range": amount, "rate": rate, "apply_url": r.apply_link, "url": r.apply_link, "county": r.county, "sector": r.sector, "description": r.requirements, "source": getattr(r, "source_url", "") or r.apply_link, "source_url": getattr(r, "source_url", "") or r.apply_link, "last_verified_at": getattr(r, "last_verified_at", None), "is_live": True, "is_curated": False})
    return templates.TemplateResponse("business_os_funding.html", {"request": request, "current_user": current_user, "user": current_user, "funders": funders, "funding": funders, "opportunities": funders, "items": funders, "data": funders, "total": len(funders), "count": len(funders), "total_funders": len(funders), "has_data": len(funders) > 0, "is_curated": False, "is_live": True, "data_source": "Live scrape of provider pages - see source_url per row", "sector": sector or "", "county": county or ""})

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_session)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None
    rows = list(db.exec(select(ExportOpportunity)).all())
    exports = [{"product": r.product, "product_name": r.product, "destination": getattr(r, "destination", None) or r.country or "", "country": getattr(r, "destination", None) or r.country or "", "destination_country": getattr(r, "destination", None) or r.country or "", "county": getattr(r, "county", None) or "", "description": getattr(r, "description", None) or "", "opportunity_score": None, "score": None, "source": getattr(r, "source_url", "") or "", "source_url": getattr(r, "source_url", "") or "", "source_name": getattr(r, "source_name", "") or "", "last_verified_at": getattr(r, "last_verified_at", None), "is_live": True, "is_curated": False} for r in rows]
    destinations = len(set(e["destination"] for e in exports if e["destination"]))
    return templates.TemplateResponse("business_os_export.html", {"request": request, "current_user": current_user, "user": current_user, "exports": exports, "opportunities": exports, "items": exports, "data": exports, "export_opportunities": exports, "total": len(exports), "count": len(exports), "total_opportunities": len(exports), "total_exports": len(exports), "scored": 0, "scored_count": 0, "destinations": destinations, "destination_count": destinations, "total_destinations": destinations, "avg_score": None, "has_data": len(exports) > 0, "is_curated": False, "is_live": True, "data_source": "Live scrape of regulator pages - see source_url per row"})

@router.post("/scrape", dependencies=[Depends(require_module(module_number=8))])
def run_scrape(request: Request, db: Session = Depends(get_session), user=Depends(get_current_user)):
    return {"status": "scraped", "funding": scrape_funding(db), "exports": scrape_exports(db)}

@router.post("/business", dependencies=[Depends(require_module(module_number=8)), Depends(consume_credits(1))])
def create_new_business(request: Request, req: BusinessCreate, session: Session = Depends(get_session), user=Depends(get_current_user)):
    try:
        return create_business(session, req, user.id)
    except Exception as e:
        logger.exception(f"create_business failed: {e}")
        raise HTTPException(status_code=500, detail="Could not create business. Please try again.")

@router.get("/business/{business_id}", dependencies=[Depends(require_module(module_number=8))])
def get_business_details(request: Request, business_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    business = get_business(session, business_id)
    if not business or business.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@router.post("/inventory/product", dependencies=[Depends(require_module(module_number=8)), Depends(consume_credits(1))])
def add_new_product(request: Request, req: ProductCreate, session: Session = Depends(get_session), user=Depends(get_current_user)):
    try:
        return add_product(session, req, user.id)
    except Exception as e:
        logger.exception(f"add_product failed: {e}")
        raise HTTPException(status_code=500, detail="Could not add product. Please try again.")

@router.get("/inventory/products/{business_id}", dependencies=[Depends(require_module(module_number=8))])
def list_products(request: Request, business_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    business = get_business(session, business_id)
    if not business or business.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your business")
    stmt = select(Product).where(Product.business_id == business_id)
    return list(session.exec(stmt))

@router.post("/accounting/invoice", dependencies=[Depends(require_module(module_number=8)), Depends(consume_credits(2))])
def create_new_invoice(request: Request, req: InvoiceCreate, session: Session = Depends(get_session), user=Depends(get_current_user)):
    try:
        return create_invoice(session, req, user.id)
    except Exception as e:
        logger.exception(f"create_invoice failed: {e}")
        raise HTTPException(status_code=500, detail="Could not create invoice. Please try again.")

@router.post("/accounting/invoice/pay", dependencies=[Depends(require_module(module_number=8))])
def pay_invoice(request: Request, req: PayInvoice, session: Session = Depends(get_session), user=Depends(get_current_user)):
    try:
        return mark_invoice_paid(session, req.invoice_id, req.mpesa_receipt, user.id)
    except Exception as e:
        logger.exception(f"pay_invoice failed: {e}")
        raise HTTPException(status_code=500, detail="Could not mark invoice as paid. Please try again.")

@router.get("/accounting/invoices/{business_id}", dependencies=[Depends(require_module(module_number=8))])
def list_invoices(request: Request, business_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    business = get_business(session, business_id)
    if not business or business.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your business")
    stmt = select(Invoice).where(Invoice.business_id == business_id)
    return list(session.exec(stmt))

@router.post("/hr/employee", dependencies=[Depends(require_module(module_number=8)), Depends(consume_credits(1))])
def add_new_employee(request: Request, req: EmployeeCreate, session: Session = Depends(get_session), user=Depends(get_current_user)):
    try:
        return add_employee(session, req, user.id)
    except Exception as e:
        logger.exception(f"add_employee failed: {e}")
        raise HTTPException(status_code=500, detail="Could not add employee. Please try again.")

@router.get("/hr/employees/{business_id}", dependencies=[Depends(require_module(module_number=8))])
def list_employees(request: Request, business_id: int, session: Session = Depends(get_session), user=Depends(get_current_user)):
    business = get_business(session, business_id)
    if not business or business.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your business")
    stmt = select(Employee).where(Employee.business_id == business_id)
    return list(session.exec(stmt))
