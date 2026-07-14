from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
from pydantic import BaseModel
from typing import List
from .service import create_business, get_business, add_product, create_invoice, add_employee
from .models import Business, Product, Invoice, Employee
from app.modules.db import get_session
from app.modules.core.guards import require_module, consume_credits

router = APIRouter(prefix="/os", tags=["Business OS"])

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

@router.post("/business")
@require_module(module_number=8)
def create_new_business(request: Request, req: BusinessCreate, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    business = create_business(session, req, user_id)
    consume_credits(session, user_id, "api_credits", 1)
    return business

@router.get("/business/{business_id}")
@require_module(module_number=8)
def get_business_details(request: Request, business_id: int, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    business = get_business(session, business_id)
    if not business or business.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@router.post("/inventory/product")
@require_module(module_number=8)
def add_new_product(request: Request, req: ProductCreate, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    consume_credits(session, user_id, "api_credits", 1)
    return add_product(session, req)

@router.get("/inventory/products/{business_id}")
@require_module(module_number=8)
def list_products(request: Request, business_id: int, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    business = get_business(session, business_id)
    if not business or business.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your business")
    return session.query(Product).filter(Product.business_id == business_id).all()

@router.post("/accounting/invoice")
@require_module(module_number=8)
def create_new_invoice(request: Request, req: InvoiceCreate, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    consume_credits(session, user_id, "api_credits", 2)
    return create_invoice(session, req)

@router.get("/accounting/invoices/{business_id}")
@require_module(module_number=8)
def list_invoices(request: Request, business_id: int, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    business = get_business(session, business_id)
    if not business or business.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your business")
    return session.query(Invoice).filter(Invoice.business_id == business_id).all()

@router.post("/hr/employee")
@require_module(module_number=8)
def add_new_employee(request: Request, req: EmployeeCreate, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    consume_credits(session, user_id, "api_credits", 1)
    return add_employee(session, req)

@router.get("/hr/employees/{business_id}")
@require_module(module_number=8)
def list_employees(request: Request, business_id: int, session: Session = Depends(get_session)):
    user_id = request.state.user.id
    business = get_business(session, business_id)
    if not business or business.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not your business")
    return session.query(Employee).filter(Employee.business_id == business_id).all()
