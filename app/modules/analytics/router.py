from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from modules.database import get_db
from modules.analytics import service

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/")
def get_analytics(db: Session = Depends(get_db)):
    return service.get_analytics(db)
