from sqlalchemy.orm import Session
from app.modules.ai_agent import models
from typing import List, Optional
from datetime import datetime

def get_all_tasks(db: Session) -> List[models.AgentTask]:
    return db.query(models.AgentTask).order_by(models.AgentTask.created_at.desc()).all()

def get_task_by_id(db: Session, task_id: int) -> Optional[models.AgentTask]:
    return db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()

def get_tasks_by_status(db: Session, status: str) -> List[models.AgentTask]:
    return db.query(models.AgentTask).filter(models.AgentTask.status == status).all()

def get_tasks_by_type(db: Session, task_type: str) -> List[models.AgentTask]:
    return db.query(models.AgentTask).filter(models.AgentTask.task_type == task_type).all()

def create_and_run_task(db: Session, task_type: str, prompt: str) -> models.AgentTask:
    db_task = models.AgentTask(
        task_type=task_type,
        prompt=prompt,
        status="processing"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Run AI logic
    response = run_ai_logic(task_type, prompt)
    
    db_task.response = response
    db_task.status = "completed" if response else "failed"
    db_task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    return db_task

def run_ai_logic(task_type: str, prompt: str) -> str:
    # TODO: Plug in OpenAI, Gemini, or Llama here
    # Example mock responses. Replace with real API call.
    
    if task_type == "email_draft":
        return f"Subject: Follow-up\nHi,\n\n{prompt}\n\nBest regards,\nTeam"
    elif task_type == "customer_reply":
        return f"Hello! Thank you for reaching out. {prompt} We will get back to you shortly."
    elif task_type == "report_summary":
        return f"Summary: {prompt[:200]}... Key insights extracted."
    elif task_type == "invoice_reminder":
        return f"Reminder: Your invoice is due. {prompt} Please complete payment to avoid late fees."
    elif task_type == "marketing_copy":
        return f"New Offer! {prompt} Limited time only. Shop now!"
    else:
        return f"AI Response for '{task_type}': {prompt}"

def update_task(db: Session, task_id: int, response: str, status: str) -> Optional[models.AgentTask]:
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db_task.response = response
        db_task.status = status
        if status == "completed":
            db_task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int) -> bool:
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db.delete(db_task)
        db.commit()
        return True
    return False
