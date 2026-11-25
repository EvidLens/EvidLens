import copy
from sqlmodel import Session, select, func
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.models import Plan, AddOn, ALCService, UserSubscription, MarketMetric
from app.modules.report_builder.models import Report
from app.core.gating import PLAN_MODULES, normalize_plan, get_active_plan, get_plan_limits

UNLIMITED = -1

PRICING = {
    "Free": {"monthly": 0, "yearly": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1, "lens": "Lite", "data_delay": "14 Days", "watermark": True},
    "Starter": {"monthly": 500, "yearly": 5000, "areas": 1, "products": 3, "users": 1, "competitors": 3, "lens": "Basic", "data_delay": "7 Days", "watermark": False},
    "Pro": {"monthly": 1500, "yearly": 15000, "areas": 3, "products": 9, "users": 5, "competitors": 10, "leads_qtr": 250, "lens": "Pro", "flag": "⭐"},
    "Enterprise": {"monthly": 5000, "yearly": 50000, "areas": 9, "products": 21, "users": UNLIMITED, "competitors": UNLIMITED, "leads_qtr": UNLIMITED, "lens": "Enterprise", "api": True, "briefings": "Weekly"},
}

class CoreService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    PRICING = PRICING

    PLAN_NAME_MAP = {
        "FREE": "Free",
        "EV-FREE": "Free",
        "STARTER": "Starter",
        "EV-STARTER": "Starter",
        "BASIC": "Starter",
        "EV-SME": "Starter",
        "SME": "Starter",
        "PRO": "Pro",
        "PROFESSIONAL": "Pro",
        "EV-GROWTH": "Pro",
        "GROWTH": "Pro",
        "EV-PRO": "Pro",
        "ENTERPRISE": "Enterprise",
        "ENT": "Enterprise",
        "EV-ENT": "Enterprise",
        "Free": "Free",
        "Starter": "Starter",
        "Pro": "Pro",
        "Enterprise": "Enterprise",
    }

    ADDONS = {
        "Slack Alerts": {"annual": 60000},
        "CRM Integration": {"setup": 125000, "annual": 60000},
        "PowerBI Export": {"annual": 150000},
        "Analyst WhatsApp": {"annual": 240000},
        "API Access": {"setup": 75000, "annual": 150000},
        "Custom Report": {"one_time": 150000},
        "Training": {"one_time": 75000},
    }

    ALC = {
        "Benchmark Report": {"price": 175000},
        "Due Diligence": {"price": 375000},
        "500 Leads": {"price": 90000},
        "Social Listening": {"price": 225000},
        "Year in Review": {"price": 250000},
        "County Deep Dive": {"price": 300000},
    }

    def _format_price(self, amount) -> str:
        if amount == UNLIMITED:
            return "Unlimited"
        if amount is None:
            return f"{settings.CURRENCY_SYMBOL} 0"
        return f"{settings.CURRENCY_SYMBOL} {amount:,}"

    def _add_display_prices(self, data: dict) -> dict:
        out = copy.deepcopy(data)
        for v in out.values():
            if isinstance(v, dict):
                for price_key in ["monthly", "yearly", "annual", "one_time", "setup", "price"]:
                    if price_key in v:
                        v[f"{price_key}_display"] = self._format_price(v[price_key])
                v["currency"] = settings.CURRENCY
        return out

    def _db_pricing(self, db: Optional[Session]) -> Optional[dict]:
        if db is None:
            return None
        try:
            plans = db.exec(select(Plan)).all()
            if not plans:
                return None
            out = {}
            for p in plans:
                code = self.PLAN_NAME_MAP.get((p.code or "").upper(), p.code)
                if code not in PRICING:
                    continue
                out[code] = {
                    "monthly": p.monthly_price or PRICING[code]["monthly"],
                    "yearly": p.annual_price or p.yearly_price or PRICING[code]["yearly"],
                    "areas": getattr(p, "areas", PRICING[code]["areas"]),
                    "products": getattr(p, "products", PRICING[code]["products"]),
                    "users": getattr(p, "users", PRICING[code]["users"]),
                    "competitors": getattr(p, "competitors", PRICING[code]["competitors"]),
                    "lens": getattr(p, "lens", PRICING[code]["lens"]),
                }
            return out if out else None
        except Exception:
            return None

    def get_all_pricing(self, db: Optional[Session] = None) -> Dict[str, Any]:
        db = db or self.db
        sectors_count = 0
        products_count = 0
        if db is not None:
            try:
                sectors_count = db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() or 0
                products_count = db.exec(select(func.count(func.distinct(MarketMetric.product)))).one() or 0
            except Exception:
                sectors_count = 0
                products_count = 0
        pricing = self._db_pricing(db) or self.PRICING
        return {
            "currency": settings.CURRENCY,
            "currency_symbol": settings.CURRENCY_SYMBOL,
            "plans": self._add_display_prices(pricing),
            "addons": self._add_display_prices(self.ADDONS),
            "ala_carte": self._add_display_prices(self.ALC),
            "sectors": sectors_count,
            "products": products_count,
            "vat_note": f"All prices {settings.CURRENCY_SYMBOL}. VAT excluded. Yearly = 10 months, 2 months free",
        }

    def get_platform_stats(self, db: Optional[Session] = None) -> Dict[str, int]:
        db = db or self.db
        if db is None:
            return {"insights": 0, "active_products": 0, "sectors": 0, "reports": 0}
        return {
            "insights": db.exec(select(func.count(MarketMetric.id))).one() or 0,
            "active_products": db.exec(select(func.count(func.distinct(MarketMetric.product)))).one() or 0,
            "sectors": db.exec(select(func.count(func.distinct(MarketMetric.sector)))).one() or 0,
            "reports": db.exec(select(func.count(Report.id))).one() or 0,
        }

    def check_access(self, db: Optional[Session] = None, user_id: int = 0, area_name: str = "") -> Dict[str, Any]:
        db = db or self.db
        if db is None or not user_id:
            return {"allowed": False, "plan": "Free", "modules": PLAN_MODULES["FREE"], "limits": self.PRICING["Free"]}
        plan = get_active_plan(db, type("U", (), {"id": user_id})())
        plan_name = self.PLAN_NAME_MAP.get(plan, "Free")
        canonical = normalize_plan(plan_name)
        modules = PLAN_MODULES.get(canonical, PLAN_MODULES["FREE"])
        if area_name and area_name not in modules:
            return {"allowed": False, "plan": plan_name, "modules": modules, "limits": self.PRICING.get(plan_name, self.PRICING["Free"]), "reason": f"{area_name} not in {plan_name} plan"}
        return {"allowed": True, "plan": plan_name, "modules": modules, "limits": get_plan_limits(canonical)}

    def health(self) -> Dict[str, Any]:
        db_ok = False
        if self.db is not None:
            try:
                self.db.exec(select(func.count(MarketMetric.id))).one()
                db_ok = True
            except Exception:
                db_ok = False
        return {"status": "ok" if db_ok or self.db is None else "degraded", "service": "evidlens-api", "currency": settings.CURRENCY, "db": "ok" if db_ok else "unknown"}

    def version(self) -> Dict[str, Any]:
        return {"version": "1.0.0", "env": settings.ENV}

_core = CoreService()

def get_all_pricing(db: Session) -> Dict[str, Any]:
    return _core.get_all_pricing(db)

def get_platform_stats(db: Session) -> Dict[str, int]:
    return _core.get_platform_stats(db)

def check_access(db: Session, user_id: int, area_name: str) -> Dict[str, Any]:
    return _core.check_access(db, user_id, area_name)
