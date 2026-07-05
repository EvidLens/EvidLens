from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.core.db import get_db
from app.modules.analytic import service

router = APIRouter(prefix="/analytic", tags=["analytic"])

class RevenueOut(BaseModel):
    total_revenue: float
    total_invoices: int

class InventorySummaryOut(BaseModel):
    total_items: int
    low_stock_count: int
    total_inventory_value: float

class TicketStatsOut(BaseModel):
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int

class DashboardOut(BaseModel):
    revenue: RevenueOut
    inventory: InventorySummaryOut
    tickets: TicketStatsOut

@router.get("/revenue", response_model=RevenueOut)
def get_revenue(db: Session = Depends(get_db)):
    return service.get_revenue_summary(db)

@router.get("/inventory", response_model=InventorySummaryOut)
def get_inventory_summary(db: Session = Depends(get_db)):
    return service.get_inventory_summary(db)

@router.get("/tickets", response_model=TicketStatsOut)
def get_ticket_stats(db: Session = Depends(get_db)):
    return service.get_ticket_stats(db)

@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    revenue = service.get_revenue_summary(db)
    inventory = service.get_inventory_summary(db)
    tickets = service.get_ticket_stats(db)
    return {
        "revenue": revenue,
        "inventory": inventory,
        "tickets": tickets
    }
