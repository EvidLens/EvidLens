from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from modules.database import get_db
from modules.support import service

router = APIRouter(prefix="/support", tags=["support"])

@router.get("/")
def get_all_tickets(db: Session = Depends(get_db)):
    return service.get_all_tickets(db)

@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return service.get_ticket_by_id(db, ticket_id)
