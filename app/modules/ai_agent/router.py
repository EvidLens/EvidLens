from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.db import get_db
from modules.ai_agent import service, models

router = APIRouter(prefix="/ai-agent", tags=["ai_agent"])

class AgentTaskOut(BaseModel):
    id: int
    task_type: str
    prompt: str
    response: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True

class AgentTaskCreate(BaseModel):
    task_type: str # email_draft, customer_reply, report_summary, invoice_reminder
    prompt: str

class AgentTaskUpdate(BaseModel):
    response: str
    status: str # pending, processing, completed, failed

@router.get("/", response_model=List[AgentTaskOut])
def get_all_tasks(db: Session = Depends(get_db)):
    return service.get_all_tasks(db)

@router.post("/run", response_model=AgentTaskOut)
def run_task(task: AgentTaskCreate, db: Session = Depends(get_db)):
    return service.create_and_run_task(db, task.task_type, task.prompt)

@router.get("/{task_id}", response_model=AgentTaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    db_task = service.get_task_by_id(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@router.put("/{task_id}", response_model=AgentTaskOut)
def update_task(task_id: int, task: AgentTaskUpdate, db: Session = Depends(get_db)):
    db_task = service.update_task(db, task_id, task.response, task.status)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    success = service.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"detail": "Task deleted successfully"}
