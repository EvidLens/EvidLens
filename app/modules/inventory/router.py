from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from modules.database import get_db
from modules.inventory import service

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.get("/")
def get_all_inventory(db: Session = Depends(get_db)):
    return service.get_all_inventory(db)

@router.get("/{item_id}")
def get_inventory_item(item_id: int, db: Session = Depends(get_db)):
    return service.get_inventory_item(db, item_id)
