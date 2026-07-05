from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

from core.db import get_db
from modules.marketing import service, models

router = APIRouter(prefix="/marketing", tags=["marketing"])

class CampaignOut(BaseModel):
    id: int
    name: str
    channel: str
    budget: float
    status: str
    start_date: datetime
    end_date: datetime

    class Config:
        orm_mode = True

class CampaignCreate(BaseModel):
    name: str
    channel: str
    budget: float
    start_date: datetime
    end_date: datetime

class CampaignUpdate(BaseModel):
    name: str
    channel: str
    budget: float
    status: str
    start_date: datetime
    end_date: datetime

@router.get("/", response_model=List[CampaignOut])
def get_all_campaigns(db: Session = Depends(get_db)):
    return service.get_all_campaigns(db)

@router.post("/", response_model=CampaignOut)
def create_campaign(campaign: CampaignCreate, db: Session = Depends(get_db)):
    return service.create_campaign(db, campaign.name, campaign.channel, campaign.budget, campaign.start_date, campaign.end_date)

@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    db_campaign = service.get_campaign_by_id(db, campaign_id)
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return db_campaign

@router.put("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, campaign: CampaignUpdate, db: Session = Depends(get_db)):
    db_campaign = service.update_campaign(db, campaign_id, campaign.name, campaign.channel, campaign.budget, campaign.status, campaign.start_date, campaign.end_date)
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return db_campaign

@router.patch("/{campaign_id}/status", response_model=CampaignOut)
def update_campaign_status(campaign_id: int, status: str, db: Session = Depends(get_db)):
    db_campaign = service.update_status(db, campaign_id, status)
    if not db_campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return db_campaign
