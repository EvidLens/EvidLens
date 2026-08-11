from sqlmodel import Session
from .models import Business, TeamMember, Product, Invoice, Employee, AuditLog, InvoiceStatus
from datetime import datetime
import uuid

def log_action(session: Session, business_id: int, user_id: int, action: str, entity: str, entity_id: int = None, details: str = None):
    log = AuditLog(business_id=business_id, user_id=user_id, action=action, entity=entity, entity_id=entity_id, details=details)
    session.add(log)
    session.commit()

def create_business(session: Session, req, user_id: int):
    db_business = Business(name=req.name, owner_id=user_id, sector=req.sector, county=req.county)
    session.add(db_business)
    session.commit()
    session.refresh(db_business)
    owner_member = TeamMember(business_id=db_business.id, user_id=user_id, role="owner")
    session.add(owner_member)
    session.commit()
    log_action(session, db_business.id, user_id, "CREATE_BUSINESS", "Business", db_business.id)
    return db_business

def get_business(session: Session, business_id: int):
    return session.get(Business, business_id)

def add_product(session: Session, req, user_id: int):
    db_product = Product(business_id=req.business_id, name=req.name, sku=req.sku, selling_price=req.selling_price, buying_price=req.buying_price, stock_qty=req.stock_qty)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    log_action(session, req.business_id, user_id, "ADD_PRODUCT", "Product", db_product.id, f"SKU: {req.sku}")
    return db_product

def create_invoice(session: Session, req, user_id: int):
    invoice_number = f"EVD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    db_invoice = Invoice(business_id=req.business_id, invoice_number=invoice_number, customer_name=req.customer_name, customer_phone=req.customer_phone, total_amount=req.total_amount, status=InvoiceStatus.draft)
    session.add(db_invoice)
    session.commit()
    session.refresh(db_invoice)
    log_action(session, req.business_id, user_id, "CREATE_INVOICE", "Invoice", db_invoice.id, f"Amount: KES {req.total_amount}")
    return db_invoice

def mark_invoice_paid(session: Session, invoice_id: int, mpesa_receipt: str, user_id: int):
    invoice = session.get(Invoice, invoice_id)
    if not invoice: return None
    invoice.status = InvoiceStatus.paid
    invoice.mpesa_receipt = mpesa_receipt
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    log_action(session, invoice.business_id, user_id, "INVOICE_PAID", "Invoice", invoice.id, f"MPESA: {mpesa_receipt}")
    return invoice

def add_employee(session: Session, req, user_id: int):
    db_employee = Employee(business_id=req.business_id, full_name=req.full_name, phone=req.phone, role=req.role, salary_kes=req.salary_kes)
    session.add(db_employee)
    session.commit()
    session.refresh(db_employee)
    log_action(session, req.business_id, user_id, "ADD_EMPLOYEE", "Employee", db_employee.id)
    return db_employee
