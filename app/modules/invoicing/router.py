from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from modules.database import get_db
from modules.invoicing import service

router = APIRouter(prefix="/invoicing", tags=["invoicing"])

@router.get("/")
def get_all_invoices(db: Session = Depends(get_db)):
    return service.get_all_invoices(db)

@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return service.get_invoice_by_id(db, invoice_id)
