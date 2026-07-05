from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import date

from app.core.db import get_db
from app.modules.invoicing import service, models

router = APIRouter(prefix="/invoicing", tags=["invoicing"])

class InvoiceOut(BaseModel):
    id: int
    case_id: int
    invoice_number: str
    amount: float
    status: str
    due_date: date

    class Config:
        orm_mode = True

class InvoiceCreate(BaseModel):
    case_id: int
    amount: float
    due_date: date

@router.get("/", response_model=List[InvoiceOut])
def get_all_invoices(db: Session = Depends(get_db)):
    return service.get_all_invoices(db)

@router.post("/", response_model=InvoiceOut)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    return service.create_invoice(db, invoice.case_id, invoice.amount, invoice.due_date)

@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    db_invoice = service.get_invoice_by_id(db, invoice_id)
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@router.patch("/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(invoice_id: int, status: str, db: Session = Depends(get_db)):
    db_invoice = service.update_invoice_status(db, invoice_id, status)
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice
