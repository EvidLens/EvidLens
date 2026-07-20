from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.modules.database import get_session
from app.modules.core.service import CoreService

router = APIRouter()

@router.get("/api/core/health")
async def health_check(db: Session = Depends(get_session)):
    service = CoreService(db)
    return service.health()

@router.get("/api/core/version")
async def version():
    service = CoreService()
    return service.version()
