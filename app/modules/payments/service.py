from sqlalchemy.orm import Session
from app.modules.payments import models
from typing import List, Optional

def get_all_payments(db: Session) -> List[models.Payment]:
    return db.query(models.Payment).all()

def get_payment_by_id(db: Session, payment_id: int) -> Optional[models.Payment]:
    return db.query(models.Payment).filter(models.Payment.id == payment_id).first()

def get_payments_by_invoice(db: Session, invoice_id: int) -> List[models.Payment]:
    return db.query(models.Payment).filter(models.Payment.invoice_id == invoice_id).all()

def get_payments_by_status(db: Session, status: str) -> List[models.Payment]:
    return db.query(models.Payment).filter(models.Payment.status == status).all()

def create_payment(db: Session, invoice_id: int, amount: float, payment_method: str, transaction_ref: str) -> models.Payment:
    db_payment = models.Payment(
        invoice_id=invoice_id,
        amount=amount,
        payment_method=payment_method,
        transaction_ref=transaction_ref
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

def update_payment(db: Session, payment_id: int, amount: float, payment_method: str, status: str, transaction_ref: str) -> Optional[models.Payment]:
    db_payment = get_payment_by_id(db, payment_id)
    if db_payment:
        db_payment.amount = amount
        db_payment.payment_method = payment_method
        db_payment.status = status
        db_payment.transaction_ref = transaction_ref
        db.commit()
        db.refresh(db_payment)
    return db_payment

def update_status(db: Session, payment_id: int, status: str) -> Optional[models.Payment]:
    db_payment = get_payment_by_id(db, payment_id)
    if db_payment:
        db_payment.status = status
        db.commit()
        db.refresh(db_payment)
    return db_payment

def delete_payment(db: Session, payment_id: int) -> bool:
    db_payment = get_payment_by_id(db, payment_id)
    if db_payment:
        db.delete(db_payment)
        db.commit()
        return True
    return False
