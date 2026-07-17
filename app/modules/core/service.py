import os
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from app.modules.core.models import Plan, AddOn, ALCService, UserSubscription
from app.modules.report_builder.models import Report
from app.modules.market_engine.models import MarketSearch

# EXACT FROM SPEC PART 3
PRICING = {
    "EV-FREE": {
        "monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1,
        "lens": "Lite", "data_delay": "14 Days", "watermark": True, "notes": "14 Days. 1 Area. 1 Product. Lens Lite"
    },
    "EV-STARTER": {
        "monthly": 0, "annual": 0, "areas": 1, "products": 1, "users": 1, "competitors": 1,
        "lens": "Lite", "data_delay": "Forever", "watermark": True, "notes": "Forever. Delayed data. Watermark. Lens Lite"
    },
    "EV-SME": {
        "monthly": 20000, "annual": 204000, "areas": 1, "products": 3, "users": 1, "competitors": 3,
        "leads_qtr": 0, "lens": "Basic", "notes": "1 Area. 3 Products. 1 User. 3 Competitors. Lens Basic"
    },
    "EV-GROWTH": {
        "monthly": 50000, "annual": 510000, "areas": 3, "products": 9, "users": 5, "competitors": 10,
        "leads_qtr": 250, "lens": "Pro", "flag": "⭐", "notes": "3 Areas. 9 Products. 5 Users. 10 Competitors. 250 Leads/Qtr. Lens Pro"
    },
    "EV-PRO": {
        "monthly": 100000, "annual": 1020000, "areas": 6, "products": 15, "users": 15, "competitors": "Unlimited",
        "leads_qtr": 1000, "lens": "Pro", "notes": "6 Areas. 15 Products. 15 Users. Unlimited Competitors. 1000 Leads/Qtr. Lens Pro"
    },
    "EV-ENT": {
        "monthly": 200000, "annual": 2040000, "areas": 9, "products": 21, "users": "Unlimited", "competitors": "Unlimited",
        "leads_qtr": "Unlimited", "lens": "Enterprise", "api": True, "briefings": "Weekly", "notes": "9 Areas. 21 Products. Unlimited Users. API. Weekly Briefings. Lens Enterprise"
    }
}

# EXACT ADDONS FROM SPEC
ADDONS = {
    "Slack Alerts": {"annual": 60000, "desc": "Real-time alerts to Slack"},
    "CRM Integration": {"setup": 125000, "annual": 60000, "desc": "Hubspot, Salesforce, Pipedrive"},
    "PowerBI Export": {"annual": 150000, "desc": "Live dashboard export"},
    "Analyst WhatsApp": {"annual": 240000, "desc": "Dedicated analyst on WhatsApp"},
    "API Access": {"setup": 75000, "annual": 150000, "desc": "Full API access to all 21 products"},
    "Custom Report": {"one_time": 150000, "desc": "Bespoke report by analysts"},
    "Training": {"one_time": 75000, "desc": "Team onboarding + training"}
}

# EXACT À LA CARTE FROM SPEC
ALC = {
    "Benchmark Report": {"price": 175000, "desc": "Compare vs top 5 competitors"},
    "Due Diligence": {"price": 375000, "desc": "Full company + financial DD"},
    "500 Leads": {"price": 90000, "desc": "B2B database export"},
    "Social Listening": {"price": 225000, "desc": "90 days brand monitoring"},
    "Year in Review": {"price": 250000, "desc": "Annual market report"},
    "County Deep Dive": {"price": 300000, "desc": "All data for 1 county"}
}

def get_all_pricing(db: Session) -> Dict[str, Any]:
    return {
        "plans": PRICING,
        "addons": ADDONS,
        "ala_carte": ALC,
        "sectors": 75,
        "products": 21,
        "vat_note": "All prices Ksh. VAT excluded. Annual = -15%"
    }

def get_platform_stats(db: Session) -> Dict[str, int]:
    return {
        "insights": db.query(func.count(MarketSearch.id)).scalar() or 0,
        "active_products": 21,
        "sectors": 75,
        "reports": db.query(func.count(Report.id)).scalar() or 0
    }

def check_access(db: Session, user_id: int, area_name: str) -> Dict[str, Any]:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub: return {"allowed": False, "plan": "EV-FREE"}
    plan = PRICING.get(sub.plan.name, PRICING["EV-FREE"])
    return {"allowed": True, "plan": sub.plan.name, "limits": plan}
