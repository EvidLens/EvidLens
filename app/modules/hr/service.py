from sqlalchemy.orm import Session
from app.modules.hr import models
from typing import List, Optional
from datetime import date

def get_all_employees(db: Session) -> List[models.Employee]:
    return db.query(models.Employee).all()

def get_employee_by_id(db: Session, employee_id: int) -> Optional[models.Employee]:
    return db.query(models.Employee).filter(models.Employee.id == employee_id).first()

def get_employee_by_email(db: Session, email: str) -> Optional[models.Employee]:
    return db.query(models.Employee).filter(models.Employee.email == email).first()

def create_employee(db: Session, name: str, email: str, role: str, hire_date: date, salary: float) -> models.Employee:
    db_employee = models.Employee(
        name=name,
        email=email,
        role=role,
        hire_date=hire_date,
        salary=salary
    )
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def update_employee(db: Session, employee_id: int, name: str, email: str, role: str, hire_date: date, salary: float, status: str) -> Optional[models.Employee]:
    db_employee = get_employee_by_id(db, employee_id)
    if db_employee:
        db_employee.name = name
        db_employee.email = email
        db_employee.role = role
        db_employee.hire_date = hire_date
        db_employee.salary = salary
        db_employee.status = status
        db.commit()
        db.refresh(db_employee)
    return db_employee

def update_status(db: Session, employee_id: int, status: str) -> Optional[models.Employee]:
    db_employee = get_employee_by_id(db, employee_id)
    if db_employee:
        db_employee.status = status
        db.commit()
        db.refresh(db_employee)
    return db_employee

def delete_employee(db: Session, employee_id: int) -> bool:
    db_employee = get_employee_by_id(db, employee_id)
    if db_employee:
        db.delete(db_employee)
        db.commit()
        return True
    return False
