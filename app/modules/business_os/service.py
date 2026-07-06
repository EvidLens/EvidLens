from sqlalchemy.orm import Session
from .models import Business, TeamMember, Product, Invoice, Employee, AuditLog, InvoiceStatus
from datetime import datetime
import uuid

def log_action(db: Session, business_id: int, user_id: int, action: str, entity: str, entity_id: int = None, details: str = None):
    log = AuditLog(
        business_id=business_id,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details
    )
    db.add(log)
    db.commit()

def create_business(db: Session, req):
    db_business = Business(
        name=req.name,
        owner_id=req.owner_id,
        sector=req.sector,
        county=req.county
    )
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    
    # Auto-add owner as team member
    owner_member = TeamMember(business_id=db_business.id, user_id=req.owner_id, role="owner")
    db.add(owner_member)
    db.commit()
    
    log_action(db, db_business.id, req.owner_id, "CREATE_BUSINESS", "Business", db_business.id)
    return db_business

def get_business(db: Session, business_id: int):
    return db.query(Business).filter(Business.id == business_id).first()

def add_product(db: Session, req):
    db_product = Product(
        business_id=req.business_id,
        name=req.name,
        sku=req.sku,
        selling_price=req.selling_price,
        buying_price=req.buying_price,
        stock_qty=req.stock_qty
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    log_action(db, req.business_id, 0, "ADD_PRODUCT", "Product", db_product.id, f"SKU: {req.sku}")
    return db_product

def create_invoice(db: Session, req):
    invoice_number = f"EVD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    db_invoice = Invoice(
        business_id=req.business_id,
        invoice_number=invoice_number,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        total_amount=req.total_amount,
        status=InvoiceStatus.draft
    )
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    log_action(db, req.business_id, 0, "CREATE_INVOICE", "Invoice", db_invoice.id, f"Amount: KES {req.total_amount}")
    return db_invoice

def mark_invoice_paid(db: Session, invoice_id: int, mpesa_receipt: str):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        return None
    invoice.status = InvoiceStatus.paid
    invoice.mpesa_receipt = mpesa_receipt
    db.commit()
    db.refresh(invoice)
    
    log_action(db, invoice.business_id, 0, "INVOICE_PAID", "Invoice", invoice.id, f"MPESA: {mpesa_receipt}")
    return invoice

def add_employee(db: Session, req):
    db_employee = Employee(
        business_id=req.business_id,
        full_name=req.full_name,
        phone=req.phone,
        role=req.role,
        salary_kes=req.salary_kes
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    
    log_action(db, req.business_id, 0, "ADD_EMPLOYEE", "Employee", db_employee.id)
    return db_employee
