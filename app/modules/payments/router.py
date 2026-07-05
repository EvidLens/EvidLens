from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.core.db import get_db
from app.modules.payments import service, models

router = APIRouter(prefix="/payments", tags=["payments"])

class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    amount: float
    payment_method: str
    status: str
    transaction_ref: str
    paid_at: datetime

    class Config:
        orm_mode = True

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    payment_method: str
    transaction_ref: str

class PaymentUpdate(BaseModel):
    amount: float
    payment_method: str
    status: str
    transaction_ref: str

@router.get("/", response_model=List[PaymentOut])
def get_all_payments(db: Session = Depends(get_db)):
    return service.get_all_payments(db)

@router.post("/", response_model=PaymentOut)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    return service.create_payment(db, payment.invoice_id, payment.amount, payment.payment_method, payment.transaction_ref)

@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = service.get_payment_by_id(db, payment_id)
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment

@router.get("/invoice/{invoice_id}", response_model=List[PaymentOut])
def get_payments_by_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return service.get_payments_by_invoice(db, invoice_id)

@router.put("/{payment_id}", response_model=PaymentOut)
def update_payment(payment_id: int, payment: PaymentUpdate, db: Session = Depends(get_db)):
    db_payment = service.update_payment(db, payment_id, payment.amount, payment.payment_method, payment.status, payment.transaction_ref)
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment

@router.delete("/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    success = service.delete_payment(db, payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"detail": "Payment deleted successfully"}
