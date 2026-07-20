import os
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from app.modules.core.models import Plan, AddOn, ALCService, UserSubscription
from app.modules.report_builder.models import Report
from app.modules.market_engine.models import MarketSearch

class CoreService:
    def __init__(self):
        pass

    # EXACT FROM SPEC PART 3
    PRICING = {
        "EV-FREE": {"monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "data_delay": "14 Days", "watermark": True},
        "EV-STARTER": {"monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "data_delay": "Forever", "watermark": True},
        "EV-SME": {"monthly": 20000, "annual": 204000, "areas": 1, "products": 3, "users": 1, "competitors": 3, "leads_qtr": 0, "lens": "Basic"},
        "EV-GROWTH": {"monthly": 50000, "annual": 510000, "areas": 3, "products": 9, "users": 5, "competitors": 10, "leads_qtr": 250, "lens": "Pro", "flag": "⭐"},
        "EV-PRO": {"monthly": 100000, "annual": 1020000, "areas": 6, "products": 15, "users": 15, "competitors": "Unlimited", "leads_qtr": 1000, "lens": "Pro"},
        "EV-ENT": {"monthly": 200000, "annual": 2040000, "areas": 9, "products": 21, "users": "Unlimited", "competitors": "Unlimited", "leads_qtr": "Unlimited", "lens": "Enterprise", "api": True, "briefings": "Weekly"}
    }

    ADDONS = {
        "Slack Alerts": {"annual": 60000}, "CRM Integration": {"setup": 125000, "annual": 60000},
        "PowerBI Export": {"annual": 150000}, "Analyst WhatsApp": {"annual": 240000},
        "API Access": {"setup": 75000, "annual": 150000}, "Custom Report": {"one_time": 150000},
        "Training": {"one_time": 75000}
    }

    ALC = {
        "Benchmark Report": {"price": 175000}, "Due Diligence": {"price": 375000},
        "500 Leads": {"price": 90000}, "Social Listening": {"price": 225000},
        "Year in Review": {"price": 250000}, "County Deep Dive": {"price": 300000}
    }

    def get_all_pricing(self, db: Session) -> Dict[str, Any]:
        return {
            "plans": self.PRICING, "addons": self.ADDONS, "ala_carte": self.ALC,
            "sectors": 75, "products": 21, "vat_note": "All prices Ksh. VAT excluded. Annual = -15%"
        }

    def get_platform_stats(self, db: Session) -> Dict[str, int]:
        return {
            "insights": db.query(func.count(MarketSearch.id)).scalar() or 0,
            "active_products": 21, "sectors": 75,
            "reports": db.query(func.count(Report.id)).scalar() or 0
        }

    def check_access(self, db: Session, user_id: int, area_name: str) -> Dict[str, Any]:
        sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
        if not sub: return {"allowed": False, "plan": "EV-FREE"}
        plan = self.PRICING.get(sub.plan.name, self.PRICING["EV-FREE"])
        return {"allowed": True, "plan": sub.plan.name, "limits": plan}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "service": "evidlens-api"}

# MODULE LEVEL ALIASES - for backward compatibility
_core = CoreService()

def get_all_pricing(db: Session) -> Dict[str, Any]:
    return _core.get_all_pricing(db)

def get_platform_stats(db: Session) -> Dict[str, int]:
    return _core.get_platform_stats(db)

def check_access(db: Session, user_id: int, area_name: str) -> Dict[str, Any]:
    return _core.check_access(db, user_id, area_name)
