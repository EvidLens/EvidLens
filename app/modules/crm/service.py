from sqlalchemy.orm import Session
from app.modules.crm import models
from typing import List

def get_all_cases(db: Session) -> List[models.Case]:
    return db.query(models.Case).all()

def get_case_by_id(db: Session, case_id: int) -> models.Case:
    return db.query(models.Case).filter(models.Case.id == case_id).first()

def create_case(db: Session, title: str, description: str) -> models.Case:
    db_case = models.Case(title=title, description=description)
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

def update_case_status(db: Session, case_id: int, status: str) -> models.Case:
    db_case = get_case_by_id(db, case_id)
    if db_case:
        db_case.status = status
        db.commit()
        db.refresh(db_case)
    return db_case
