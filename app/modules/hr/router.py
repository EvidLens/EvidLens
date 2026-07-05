from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import date

from core.db import get_db
from modules.hr import service, models

router = APIRouter(prefix="/hr", tags=["hr"])

class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    hire_date: date
    salary: float
    status: str

    class Config:
        orm_mode = True

class EmployeeCreate(BaseModel):
    name: str
    email: str
    role: str
    hire_date: date
    salary: float

class EmployeeUpdate(BaseModel):
    name: str
    email: str
    role: str
    hire_date: date
    salary: float
    status: str

@router.get("/", response_model=List[EmployeeOut])
def get_all_employees(db: Session = Depends(get_db)):
    return service.get_all_employees(db)

@router.post("/", response_model=EmployeeOut)
def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    return service.create_employee(db, employee.name, employee.email, employee.role, employee.hire_date, employee.salary)

@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    db_employee = service.get_employee_by_id(db, employee_id)
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return db_employee

@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, employee: EmployeeUpdate, db: Session = Depends(get_db)):
    db_employee = service.update_employee(db, employee_id, employee.name, employee.email, employee.role, employee.hire_date, employee.salary, employee.status)
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return db_employee

@router.patch("/{employee_id}/status", response_model=EmployeeOut)
def update_employee_status(employee_id: int, status: str, db: Session = Depends(get_db)):
    db_employee = service.update_status(db, employee_id, status)
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return db_employee
