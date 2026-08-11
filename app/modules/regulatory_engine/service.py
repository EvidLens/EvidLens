import os
import httpx
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.modules.regulatory_engine.models import Regulation, ComplianceDeadline
from app.modules.db import redis_client

async def get_regulations(db: Session, sector: str, regulator: str) -> Dict[str, Any]:
    regs = db.query(Regulation).filter(Regulation.sector == sector).all()
    if regulator: regs = [r for r in regs if regulator in r.regulator]

    async with httpx.AsyncClient(timeout=30) as client:
        cbk = await client.get("https://www.centralbank.go.ke/cbkWebsite/circulars")

    return {
        "regulations": [{"title": r.title, "regulator": r.regulator, "date": str(r.date), "summary": r.summary} for r in regs],
        "cbk_circulars": cbk.json() if cbk.status_code == 200 else []
    }

async def get_compliance_deadlines(db: Session, sector: str) -> List[Dict[str, Any]]:
    deadlines = db.query(ComplianceDeadline).filter(ComplianceDeadline.sector == sector).all()
    return [{"title": d.title, "regulator": d.regulator, "deadline": str(d.deadline), "penalty": d.penalty} for d in deadlines]
