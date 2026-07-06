from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from .service import create_business, get_business, add_product, create_invoice, add_employee
from .models import Business, Product, Invoice, Employee
from app.modules.database import get_db

router = APIRouter()

class BusinessCreate(BaseModel):
    name: str
    owner_id: int
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
def create_new_business(req: BusinessCreate, db: Session = Depends(get_db)):
    return create_business(db, req)

@router.get("/business/{business_id}")
def get_business_details(business_id: int, db: Session = Depends(get_db)):
    business = get_business(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@router.post("/inventory/product")
def add_new_product(req: ProductCreate, db: Session = Depends(get_db)):
    return add_product(db, req)

@router.get("/inventory/products/{business_id}")
def list_products(business_id: int, db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.business_id == business_id).all()

@router.post("/accounting/invoice")
def create_new_invoice(req: InvoiceCreate, db: Session = Depends(get_db)):
    return create_invoice(db, req)

@router.get("/accounting/invoices/{business_id}")
def list_invoices(business_id: int, db: Session = Depends(get_db)):
    return db.query(Invoice).filter(Invoice.business_id == business_id).all()

@router.post("/hr/employee")
def add_new_employee(req: EmployeeCreate, db: Session = Depends(get_db)):
    return add_employee(db, req)

@router.get("/hr/employees/{business_id}")
def list_employees(business_id: int, db: Session = Depends(get_db)):
    return db.query(Employee).filter(Employee.business_id == business_id).all()
