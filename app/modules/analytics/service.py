from sqlalchemy.orm import Session
from sqlalchemy import func
from modules.invoicing import models as invoice_models
from modules.inventory import models as inventory_models
from modules.support import models as support_models
from typing import Dict

def get_revenue_summary(db: Session) -> Dict:
    total_revenue = db.query(func.sum(invoice_models.Invoice.total_amount)).scalar() or 0.0
    total_invoices = db.query(func.count(invoice_models.Invoice.id)).scalar() or 0
    return {
        "total_revenue": float(total_revenue),
        "total_invoices": total_invoices
    }

def get_inventory_summary(db: Session) -> Dict:
    total_items = db.query(func.count(inventory_models.Item.id)).scalar() or 0
    low_stock_count = db.query(func.count(inventory_models.Item.id)).filter(inventory_models.Item.quantity < 10).scalar() or 0
    total_inventory_value = db.query(func.sum(inventory_models.Item.quantity * inventory_models.Item.price)).scalar() or 0.0
    return {
        "total_items": total_items,
        "low_stock_count": low_stock_count,
        "total_inventory_value": float(total_inventory_value)
    }

def get_ticket_stats(db: Session) -> Dict:
    open_tickets = db.query(func.count(support_models.Ticket.id)).filter(support_models.Ticket.status == "open").scalar() or 0
    in_progress_tickets = db.query(func.count(support_models.Ticket.id)).filter(support_models.Ticket.status == "in_progress").scalar() or 0
    resolved_tickets = db.query(func.count(support_models.Ticket.id)).filter(support_models.Ticket.status == "resolved").scalar() or 0
    return {
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "resolved_tickets": resolved_tickets
    }
