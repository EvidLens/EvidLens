from fastapi import APIRouter, Depends, BackgroundTasks
from sqlmodel import Session
from app.modules.database import get_session
from app.modules.cron.service import CronService

router = APIRouter()

@router.post("/api/cron/run/{job_name}")
async def run_cron_job(job_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_session)):
    service = CronService(db)
    background_tasks.add_task(service.run_job, job_name)
    return service.get_job_response(job_name)
