from sqlalchemy.orm import Session
from modules.invoicing import models
from typing import List, Optional
from datetime import date

def get_all_invoices(db: Session) -> List[models.Invoice]:
    return db.query(models.Invoice).all()

def get_invoice_by_id(db: Session, invoice_id: int) -> Optional[models.Invoice]:
    return db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()

def generate_invoice_number(db: Session) -> str:
    last_invoice = db.query(models.Invoice).order_by(models.Invoice.id.desc()).first()
    next_id = 1 if not last_invoice else last_invoice.id + 1
    return f"INV-{next_id:04d}"

def create_invoice(db: Session, case_id: int, amount: float, due_date: date) -> models.Invoice:
    invoice_number = generate_invoice_number(db)
    db_invoice = models.Invoice(
        case_id=case_id,
        invoice_number=invoice_number,
        amount=amount,
        due_date=due_date
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def update_invoice_status(db: Session, invoice_id: int, status: str) -> Optional[models.Invoice]:
    db_invoice = get_invoice_by_id(db, invoice_id)
    if db_invoice:
        db_invoice.status = status
        db.commit()
        db.refresh(db_invoice)
    return db_invoice
