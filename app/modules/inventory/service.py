from sqlalchemy.orm import Session
from modules.inventory import models
from typing import List, Optional

def get_all_items(db: Session) -> List[models.Item]:
    return db.query(models.Item).all()

def get_item_by_id(db: Session, item_id: int) -> Optional[models.Item]:
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def get_item_by_sku(db: Session, sku: str) -> Optional[models.Item]:
    return db.query(models.Item).filter(models.Item.sku == sku).first()

def create_item(db: Session, name: str, sku: str, quantity: int, price: float) -> models.Item:
    db_item = models.Item(name=name, sku=sku, quantity=quantity, price=price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_item(db: Session, item_id: int, name: str, sku: str, quantity: int, price: float) -> Optional[models.Item]:
    db_item = get_item_by_id(db, item_id)
    if db_item:
        db_item.name = name
        db_item.sku = sku
        db_item.quantity = quantity
        db_item.price = price
        db.commit()
        db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int) -> bool:
    db_item = get_item_by_id(db, item_id)
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False

def adjust_stock(db: Session, item_id: int, delta: int) -> Optional[models.Item]:
    db_item = get_item_by_id(db, item_id)
    if db_item:
        db_item.quantity = db_item.quantity + delta
        db.commit()
        db.refresh(db_item)
    return db_item
