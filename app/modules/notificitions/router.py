from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from app.modules.database import get_session
from app.modules.notifications.service import NotificationService

router = APIRouter()

class NotificationRequest(BaseModel):
    user_id: int
    message: str
    type: str = "info"
    channel: str = "in_app"

@router.post("/api/notifications/send")
async def send_notification(req: NotificationRequest, db: Session = Depends(get_session)):
    service = NotificationService(db)
    return await service.send(req.user_id, req.message, req.type, req.channel)

@router.get("/api/notifications/user/{user_id}")
async def get_user_notifications(user_id: int, db: Session = Depends(get_session)):
    service = NotificationService(db)
    return await service.get_for_user(user_id)
