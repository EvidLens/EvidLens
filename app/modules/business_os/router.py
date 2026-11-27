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

FUNDING_DIRECTORY = [
    {"name": "Equity Bank - SME Loan", "type": "Bank", "amount": "KES 50,000 - 5,000,000", "rate": "From 14% p.a.", "apply_url": "https://equitygroupholdings.com/ke/borrow/", "county": "All Counties", "sector": "All Sectors", "description": "Working capital and asset finance for registered SMEs with 6+ months trading history."},
    {"name": "KCB Bank - Biashara Loan", "type": "Bank", "amount": "KES 100,000 - 10,000,000", "rate": "From 13.5% p.a.", "apply_url": "https://ke.kcbgroup.com/for-business/borrow", "county": "All Counties", "sector": "All Sectors", "description": "Unsecured business loans for SMEs with KCB account and M-Pesa statements."},
    {"name": "Co-operative Bank - MSME Loan", "type": "Bank", "amount": "KES 50,000 - 3,000,000", "rate": "From 14% p.a.", "apply_url": "https://www.co-opbank.co.ke/business-banking/", "county": "All Counties", "sector": "Agriculture, Retail", "description": "MSME loans with flexible repayment for agribusiness and retail."},
    {"name": "Family Bank - Biashara Boost", "type": "Bank", "amount": "KES 30,000 - 2,000,000", "rate": "From 15% p.a.", "apply_url": "https://familybank.co.ke/", "county": "All Counties", "sector": "Retail, Services", "description": "Quick SME loans for traders and service businesses."},
    {"name": "Stima SACCO - Business Loan", "type": "SACCO", "amount": "KES 50,000 - 5,000,000", "rate": "From 12% p.a.", "apply_url": "https://www.stima-sacco.com/", "county": "All Counties", "sector": "All Sectors", "description": "SACCO loan up to 3x savings for members with 6 months membership."},
    {"name": "Kenya Youth Employment & Opportunities Project", "type": "Grant / Government", "amount": "KES 50,000 - 500,000", "rate": "Grant", "apply_url": "https://www.youthfund.go.ke/", "county": "All Counties", "sector": "Youth-led Businesses", "description": "Grants and business support for youth-led enterprises aged 18-35."},
    {"name": "Uwezo Fund", "type": "Grant / Government", "amount": "KES 50,000 - 500,000", "rate": "0% - Grant / Loan", "apply_url": "https://www.uwezofund.go.ke/", "county": "All Counties", "sector": "Women, Youth, PWD Groups", "description": "Government fund for women, youth and PWD groups for business expansion."},
    {"name": "Hustler Fund - Business", "type": "Government Loan", "amount": "KES 500 - 50,000", "rate": "8% p.a.", "apply_url": "https://www.hustlerfund.go.ke/", "county": "All Counties", "sector": "Micro Businesses", "description": "Government micro-loan via *254# for small traders and hustlers."},
]

EXPORT_DIRECTORY = [
    {"product": "Tea", "destination": "United Kingdom", "county": "Nyeri, Kericho", "description": "High demand for Kenyan black tea. Requires KEBS + Tea Board of Kenya licence."},
    {"product": "Coffee", "destination": "Germany", "county": "Nyeri, Kirinyaga", "description": "Specialty AA coffee demand in EU. Requires Coffee Directorate licence."},
    {"product": "Avocado", "destination": "United Arab Emirates", "county": "Muranga, Nyeri", "description": "Hass avocado demand year-round. Requires KEPHIS phytosanitary certificate."},
    {"product": "Macadamia", "destination": "China", "county": "Embu, Nyeri", "description": "Growing demand for in-shell macadamia. Requires AFA Nuts Directorate licence."},
    {"product": "Horticulture - Green Beans", "destination": "Netherlands / EU", "county": "Kirinyaga, Muranga", "description": "EU export under GlobalG.A.P. certification. Cold chain required."},
    {"product": "Dried Fruits - Mango", "destination": "United States", "county": "Machakos, Makueni", "description": "Dried mango snacks demand. Requires FDA facility registration."},
]

def _normalize_funder(f):
    return {
        "name": f.get("name", ""),
        "funder_name": f.get("name", ""),
        "type": f.get("type", ""),
        "funder_type": f.get("type", ""),
        "amount": f.get("amount", ""),
        "amount_range": f.get("amount", ""),
        "amount_kes": f.get("amount", ""),
        "rate": f.get("rate", ""),
        "apply_url": f.get("apply_url", ""),
        "url": f.get("apply_url", ""),
        "county": f.get("county", ""),
        "sector": f.get("sector", ""),
        "description": f.get("description", ""),
        "source": "Curated Directory - Verify with provider",
        "is_curated": True,
        "is_live": False,
    }

def _normalize_export(e):
    return {
        "product": e.get("product", ""),
        "product_name": e.get("product", ""),
        "destination": e.get("destination", ""),
        "country": e.get("destination", ""),
        "destination_country": e.get("destination", ""),
        "county": e.get("county", ""),
        "description": e.get("description", ""),
        "opportunity_score": None,
        "score": None,
        "source": "Curated Directory - Verify with buyer / regulator",
        "is_curated": True,
        "is_live": False,
    }

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, sector: Optional[str] = Query(None), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None
    funders_raw = FUNDING_DIRECTORY
    if sector:
        funders_raw = [f for f in funders_raw if sector.lower() in (f["sector"] or "").lower() or "all sectors" in (f["sector"] or "").lower()]
    if county:
        funders_raw = [f for f in funders_raw if county.lower() in (f["county"] or "").lower() or "all counties" in (f["county"] or "").lower()]
    funders = [_normalize_funder(f) for f in funders_raw]
    return templates.TemplateResponse("business_os_funding.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "funders": funders,
        "funding": funders,
        "opportunities": funders,
        "items": funders,
        "data": funders,
        "total": len(funders),
        "count": len(funders),
        "total_funders": len(funders),
        "has_data": len(funders) > 0,
        "is_curated": True,
        "data_source": "Curated Directory - Verify with provider",
        "sector": sector or "",
        "county": county or "",
    })

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_session)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None
    exports = [_normalize_export(e) for e in EXPORT_DIRECTORY]
    destinations = len(set(e["destination"] for e in exports))
    return templates.TemplateResponse("business_os_export.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "exports": exports,
        "opportunities": exports,
        "items": exports,
        "data": exports,
        "export_opportunities": exports,
        "total": len(exports),
        "count": len(exports),
        "total_opportunities": len(exports),
        "total_exports": len(exports),
        "scored": 0,
        "scored_count": 0,
        "destinations": destinations,
        "destination_count": destinations,
        "total_destinations": destinations,
        "avg_score": None,
        "has_data": len(exports) > 0,
        "is_curated": True,
        "data_source": "Curated Directory - Verify with buyer / regulator",
    })

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
