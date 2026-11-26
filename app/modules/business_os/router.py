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

CURATED_FUNDERS = [
    {"name": "Equity Bank - SME Loan", "type": "Bank", "amount": "KES 50,000 - 5,000,000", "rate": "From 14% p.a.", "apply_url": "https://equitygroupholdings.com/ke/borrow/", "county": "All Counties", "sector": "All Sectors", "description": "Working capital and asset finance for registered SMEs with 6+ months trading history."},
    {"name": "KCB Bank - Biashara Loan", "type": "Bank", "amount": "KES 100,000 - 10,000,000", "rate": "From 13.5% p.a.", "apply_url": "https://ke.kcbgroup.com/for-business/borrow", "county": "All Counties", "sector": "All Sectors", "description": "Unsecured business loans for SMEs with KCB account and M-Pesa statements."},
    {"name": "Co-operative Bank - MSME Loan", "type": "Bank", "amount": "KES 50,000 - 3,000,000", "rate": "From 14% p.a.", "apply_url": "https://www.co-opbank.co.ke/business-banking/", "county": "All Counties", "sector": "Agriculture, Retail", "description": "MSME loans with flexible repayment for agribusiness and retail."},
    {"name": "Family Bank - Biashara Boost", "type": "Bank", "amount": "KES 30,000 - 2,000,000", "rate": "From 15% p.a.", "apply_url": "https://familybank.co.ke/", "county": "All Counties", "sector": "Retail, Services", "description": "Quick SME loans for traders and service businesses."},
    {"name": "Stima SACCO - Business Loan", "type": "SACCO", "amount": "KES 50,000 - 5,000,000", "rate": "From 12% p.a.", "apply_url": "https://www.stima-sacco.com/", "county": "All Counties", "sector": "All Sectors", "description": "SACCO loan up to 3x savings for members with 6 months membership."},
    {"name": "Kenya Youth Employment & Opportunities Project", "type": "Grant / Government", "amount": "KES 50,000 - 500,000", "rate": "Grant", "apply_url": "https://www.youthfund.go.ke/", "county": "All Counties", "sector": "Youth-led Businesses", "description": "Grants and business support for youth-led enterprises aged 18-35."},
    {"name": "Uwezo Fund", "type": "Grant / Government", "amount": "KES 50,000 - 500,000", "rate": "0% - Grant / Loan", "apply_url": "https://www.uwezofund.go.ke/", "county": "All Counties", "sector": "Women, Youth, PWD Groups", "description": "Government fund for women, youth and PWD groups for business expansion."},
    {"name": "Hustler Fund - Business", "type": "Government Loan", "amount": "KES 500 - 50,000", "rate": "8% p.a.", "apply_url": "https://www.hustlerfund.go.ke/", "county": "All Counties", "sector": "Micro Businesses", "description": "Government micro-loan via *254# for small traders and hustlers."},
]

CURATED_EXPORTS = [
    {"product": "Tea", "destination": "United Kingdom", "score": 88, "county": "Nyeri, Kericho", "description": "High demand for Kenyan black tea. Requires KEBS + Tea Board of Kenya licence."},
    {"product": "Coffee", "destination": "Germany", "score": 86, "county": "Nyeri, Kirinyaga", "description": "Specialty AA coffee demand in EU. Requires Coffee Directorate licence."},
    {"product": "Avocado", "destination": "United Arab Emirates", "score": 84, "county": "Muranga, Nyeri", "description": "Hass avocado demand year-round. Requires KEPHIS phytosanitary certificate."},
    {"product": "Macadamia", "destination": "China", "score": 82, "county": "Embu, Nyeri", "description": "Growing demand for in-shell macadamia. Requires AFA Nuts Directorate licence."},
    {"product": "Horticulture - Green Beans", "destination": "Netherlands / EU", "score": 80, "county": "Kirinyaga, Muranga", "description": "EU export under GlobalG.A.P. certification. Cold chain required."},
    {"product": "Dried Fruits - Mango", "destination": "United States", "score": 76, "county": "Machakos, Makueni", "description": "Dried mango snacks demand. Requires FDA facility registration."},
]

@router.get("/funding", response_class=HTMLResponse)
async def funding_page(request: Request, sector: Optional[str] = Query(None), county: Optional[str] = Query(None), db: Session = Depends(get_session)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None
    funders = CURATED_FUNDERS
    if sector:
        funders = [f for f in funders if sector.lower() in (f["sector"] or "").lower() or "all sectors" in (f["sector"] or "").lower()]
    if county:
        funders = [f for f in funders if county.lower() in (f["county"] or "").lower() or "all counties" in (f["county"] or "").lower()]
    return templates.TemplateResponse("business_os_funding.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "funders": funders,
        "funding": funders,
        "opportunities": funders,
        "total": len(funders),
        "has_data": len(funders) > 0,
        "sector": sector or "",
        "county": county or "",
    })

@router.get("/export", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_session)):
    try:
        current_user = await get_current_user(request, db)
    except Exception:
        current_user = None
    exports = CURATED_EXPORTS
    return templates.TemplateResponse("business_os_export.html", {
        "request": request,
        "current_user": current_user,
        "user": current_user,
        "exports": exports,
        "opportunities": exports,
        "total": len(exports),
        "scored": len(exports),
        "destinations": len(set(e["destination"] for e in exports)),
        "has_data": len(exports) > 0,
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
