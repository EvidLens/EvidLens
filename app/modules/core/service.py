import os
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.modules.core.models import Plan, AddOn, ALCService, UserSubscription

PRICING = {
    "EV-FREE": {"monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "notes": "14 Days. Watermark"},
    "EV-STARTER": {"monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "notes": "Forever. Delayed data. Watermark"},
    "EV-SME": {"monthly": 20000, "annual": 204000, "areas": 1, "products": 3, "users": 1, "competitors": 3, "leads_qtr": 0, "lens": "Basic"},
    "EV-GROWTH": {"monthly": 50000, "annual": 510000, "areas": 3, "products": 9, "users": 5, "competitors": 10, "leads_qtr": 250, "lens": "Pro", "flag": "⭐"},
    "EV-PRO": {"monthly": 100000, "annual": 1020000, "areas": 6, "products": 15, "users": 15, "competitors": "Unlimited", "leads_qtr": 1000, "lens": "Pro"},
    "EV-ENT": {"monthly": 200000, "annual": 2040000, "areas": 9, "products": 21, "users": "Unlimited", "competitors": "Unlimited", "leads_qtr": "Unlimited", "lens": "Enterprise", "api": True, "briefings": "Weekly"}
}

ADDONS = {
    "Slack Alerts": {"annual": 60000},
    "CRM Integration": {"setup": 125000, "annual": 60000},
    "PowerBI Export": {"annual": 150000},
    "Analyst WhatsApp": {"annual": 240000},
    "API Access": {"setup": 75000, "annual": 150000},
    "Custom Report": {"one_time": 150000},
    "Training": {"one_time": 75000}
}

ALC = {
    "Benchmark Report": 175000,
    "Due Diligence": 375000,
    "500 Leads": 90000,
    "Social Listening": 225000,
    "Year in Review": 250000,
    "County Deep Dive": 300000
}

def get_all_pricing(db: Session) -> Dict[str, Any]:
    plans_db = db.query(Plan).all()
    return {
        "plans": PRICING,
        "addons": ADDONS,
        "ala_carte": ALC,
        "sectors": 75,
        "products": 21,
        "vat_note": "All prices Ksh. VAT excluded. Annual = -15%"
    }

def check_access(db: Session, user_id: int, area_name: str) -> bool:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub: return False
    plan = PRICING.get(sub.plan.name, PRICING["EV-FREE"])
    return True
