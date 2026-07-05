from sqlalchemy.orm import Session
from app.modules.marketing import models
from typing import List, Optional
from datetime import datetime

def get_all_campaigns(db: Session) -> List[models.Campaign]:
    return db.query(models.Campaign).all()

def get_campaign_by_id(db: Session, campaign_id: int) -> Optional[models.Campaign]:
    return db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()

def get_campaigns_by_status(db: Session, status: str) -> List[models.Campaign]:
    return db.query(models.Campaign).filter(models.Campaign.status == status).all()

def get_campaigns_by_channel(db: Session, channel: str) -> List[models.Campaign]:
    return db.query(models.Campaign).filter(models.Campaign.channel == channel).all()

def create_campaign(db: Session, name: str, channel: str, budget: float, start_date: datetime, end_date: datetime) -> models.Campaign:
    db_campaign = models.Campaign(
        name=name,
        channel=channel,
        budget=budget,
        start_date=start_date,
        end_date=end_date
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

def update_campaign(db: Session, campaign_id: int, name: str, channel: str, budget: float, status: str, start_date: datetime, end_date: datetime) -> Optional[models.Campaign]:
    db_campaign = get_campaign_by_id(db, campaign_id)
    if db_campaign:
        db_campaign.name = name
        db_campaign.channel = channel
        db_campaign.budget = budget
        db_campaign.status = status
        db_campaign.start_date = start_date
        db_campaign.end_date = end_date
        db.commit()
        db.refresh(db_campaign)
    return db_campaign

def update_status(db: Session, campaign_id: int, status: str) -> Optional[models.Campaign]:
    db_campaign = get_campaign_by_id(db, campaign_id)
    if db_campaign:
        db_campaign.status = status
        db.commit()
        db.refresh(db_campaign)
    return db_campaign

def delete_campaign(db: Session, campaign_id: int) -> bool:
    db_campaign = get_campaign_by_id(db, campaign_id)
    if db_campaign:
        db.delete(db_campaign)
        db.commit()
        return True
    return False
