from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/crm", tags=["crm"])

# TEMP: Fake CRM storage. We add DB later
fake_cases = []

class Case(BaseModel):
    id: int
    title: str
    description: str
    status: str = "open"

class CaseCreate(BaseModel):
    title: str
    description: str

@router.get("/", response_model=List[Case])
def get_all_cases():
    return fake_cases

@router.post("/", response_model=Case)
def create_case(case: CaseCreate):
    new_case = Case(
        id=len(fake_cases) + 1,
        title=case.title,
        description=case.description,
        status="open"
    )
    fake_cases.append(new_case)
    return new_case

@router.get("/{case_id}", response_model=Case)
def get_case(case_id: int):
    for case in fake_cases:
        if case.id == case_id:
            return case
    raise HTTPException(status_code=404, detail="Case not found")

@router.patch("/{case_id}")
def update_case_status(case_id: int, status: str):
    for case in fake_cases:
        if case.id == case_id:
            case.status = status
            return {"message": "Case updated", "case": case}
    raise HTTPException(status_code=404, detail="Case not found")
