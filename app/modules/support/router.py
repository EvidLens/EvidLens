from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.core.db import get_db
from app.modules.support import service, models

router = APIRouter(prefix="/support", tags=["support"])

class TicketOut(BaseModel):
    id: int
    customer_name: str
    subject: str
    description: str
    status: str
    priority: str
    assigned_to: int
    created_at: datetime

    class Config:
        orm_mode = True

class TicketCreate(BaseModel):
    customer_name: str
    subject: str
    description: str
    priority: str
    assigned_to: int

class TicketUpdate(BaseModel):
    customer_name: str
    subject: str
    description: str
    status: str
    priority: str
    assigned_to: int

@router.get("/", response_model=List[TicketOut])
def get_all_tickets(db: Session = Depends(get_db)):
    return service.get_all_tickets(db)

@router.post("/", response_model=TicketOut)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    return service.create_ticket(db, ticket.customer_name, ticket.subject, ticket.description, ticket.priority, ticket.assigned_to)

@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    db_ticket = service.get_ticket_by_id(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket

@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_db)):
    db_ticket = service.update_ticket(db, ticket_id, ticket.customer_name, ticket.subject, ticket.description, ticket.status, ticket.priority, ticket.assigned_to)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket

@router.patch("/{ticket_id}/status", response_model=TicketOut)
def update_ticket_status(ticket_id: int, status: str, db: Session = Depends(get_db)):
    db_ticket = service.update_status(db, ticket_id, status)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket
