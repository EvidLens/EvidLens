import os
from sqlmodel import Session, select, func
from typing import Dict, Any, List, Union
from app.core.config import settings
from app.modules.core.models import Plan, AddOn, ALCService, UserSubscription, MarketMetric, Report

UNLIMITED = -1

class CoreService:
    def __init__(self):
        pass

    PRICING = {
        "EV-FREE": {"monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "data_delay": "14 Days", "watermark": True},
        "EV-STARTER": {"monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "data_delay": "Forever", "watermark": True},
        "EV-SME": {"monthly": 20000, "annual": 204000, "areas": 1, "products": 3, "users": 1, "competitors": 3, "leads_qtr": 0, "lens": "Basic"},
        "EV-GROWTH": {"monthly": 50000, "annual": 510000, "areas": 3, "products": 9, "users": 5, "competitors": 10, "leads_qtr": 250, "lens": "Pro", "flag": "⭐"},
        "EV-PRO": {"monthly": 100000, "annual": 1020000, "areas": 6, "products": 15, "users": UNLIMITED, "competitors": UNLIMITED, "leads_qtr": 1000, "lens": "Pro"},
        "EV-ENT": {"monthly": 200000, "annual": 2040000, "areas": 9, "products": 21, "users": UNLIMITED, "competitors": UNLIMITED, "leads_qtr": UNLIMITED, "lens": "Enterprise", "api": True, "briefings": "Weekly"}
    }

    # TRANSLATE OLD UI NAMES TO NEW BACKEND NAMES
    PLAN_NAME_MAP = {
        "BASIC": "EV-SME",
        "PROFESSIONAL": "EV-GROWTH", 
        "ENTERPRISE": "EV-ENT"
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

    def _format_price(self, amount: Union[int, float]) -> str:
        if amount == UNLIMITED: return "Unlimited"
        return f"{settings.CURRENCY_SYMBOL} {amount:,}"
    
    def _add_display_prices(self, data: dict) -> dict:
        for k, v in data.items():
            if isinstance(v, dict):
                for price_key in ["monthly", "annual", "one_time", "setup", "price"]:
                    if price_key in v: v[f"{price_key}_display"] = self._format_price(v[price_key])
                v["currency"] = settings.CURRENCY
        return data

    def get_all_pricing(self, db: Session) -> Dict[str, Any]:
        sectors_count = db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() or 75
        products_count = db.exec(select(func.count(func.distinct(MarketMetric.product)))).one() or 21
        return {
            "currency": settings.CURRENCY,
            "currency_symbol": settings.CURRENCY_SYMBOL,
            "plans": self._add_display_prices(self.PRICING), 
            "addons": self._add_display_prices(self.ADDONS), 
            "ala_carte": self._add_display_prices(self.ALC),
            "sectors": sectors_count, 
            "products": products_count, 
            "vat_note": f"All prices {settings.CURRENCY_SYMBOL}. VAT excluded. Annual = -15%"
        }

    def get_platform_stats(self, db: Session) -> Dict[str, int]:
        return {
            "insights": db.exec(select(func.count(MarketMetric.id))).one() or 0,
            "active_products": db.exec(select(func.count(func.distinct(MarketMetric.product)))).one() or 21, 
            "sectors": db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() or 75,
            "reports": db.exec(select(func.count(Report.id))).one() or 0
        }

    def check_access(self, db: Session, user_id: int, area_name: str) -> Dict[str, Any]:
        sub = db.exec(select(UserSubscription).where(UserSubscription.user_id == user_id, UserSubscription.status == "active")).first()
        if not sub: 
            return {"allowed": False, "plan": "EV-FREE"}
        
        plan_name = sub.plan_code
        plan_name = self.PLAN_NAME_MAP.get(plan_name, plan_name) # THIS FIXES BASIC -> EV-SME
        
        plan = self.PRICING.get(plan_name, self.PRICING["EV-FREE"])
        return {"allowed": True, "plan": plan_name, "limits": plan}

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "service": "evidlens-api", "currency": settings.CURRENCY}

    def version(self) -> Dict[str, Any]:
        return {"version": "1.0.0", "env": settings.ENV}

_core = CoreService()

def get_all_pricing(db: Session) -> Dict[str, Any]:
    return _core.get_all_pricing(db)

def get_platform_stats(db: Session) -> Dict[str, int]:
    return _core.get_platform_stats(db)

def check_access(db: Session, user_id: int, area_name: str) -> Dict[str, Any]:
    return _core.check_access(db, user_id, area_name)
