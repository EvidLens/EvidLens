from sqlalchemy.orm import Session
from app.modules.support import models
from typing import List, Optional

def get_all_tickets(db: Session) -> List[models.Ticket]:
    return db.query(models.Ticket).all()

def get_ticket_by_id(db: Session, ticket_id: int) -> Optional[models.Ticket]:
    return db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()

def get_tickets_by_status(db: Session, status: str) -> List[models.Ticket]:
    return db.query(models.Ticket).filter(models.Ticket.status == status).all()

def get_tickets_by_employee(db: Session, employee_id: int) -> List[models.Ticket]:
    return db.query(models.Ticket).filter(models.Ticket.assigned_to == employee_id).all()

def create_ticket(db: Session, customer_name: str, subject: str, description: str, priority: str, assigned_to: int) -> models.Ticket:
    db_ticket = models.Ticket(
        customer_name=customer_name,
        subject=subject,
        description=description,
        priority=priority,
        assigned_to=assigned_to
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def update_ticket(db: Session, ticket_id: int, customer_name: str, subject: str, description: str, status: str, priority: str, assigned_to: int) -> Optional[models.Ticket]:
    db_ticket = get_ticket_by_id(db, ticket_id)
    if db_ticket:
        db_ticket.customer_name = customer_name
        db_ticket.subject = subject
        db_ticket.description = description
        db_ticket.status = status
        db_ticket.priority = priority
        db_ticket.assigned_to = assigned_to
        db.commit()
        db.refresh(db_ticket)
    return db_ticket

def update_status(db: Session, ticket_id: int, status: str) -> Optional[models.Ticket]:
    db_ticket = get_ticket_by_id(db, ticket_id)
    if db_ticket:
        db_ticket.status = status
        db.commit()
        db.refresh(db_ticket)
    return db_ticket

def delete_ticket(db: Session, ticket_id: int) -> bool:
    db_ticket = get_ticket_by_id(db, ticket_id)
    if db_ticket:
        db.delete(db_ticket)
        db.commit()
        return True
    return False
