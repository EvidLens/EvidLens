# app/modules/__init__.py
"""
EvidLens Core Modules
Kenya's Decision Intelligence Platform
"""

__version__ = "1.0.0"

# Import all 9 Lanes so FastAPI can register them
from . import market_engine        # Lane 1
from . import consumer_voice       # Lane 2  
from . import data_layer           # Lane 3
from . import ai_insight           # Lane 4
from . import report_builder       # Lane 5
from . import location_intel       # Lane 6
from . import knowledge_base       # Lane 7
from . import business_os          # Lane 8
from . import custom_research      # Lane 9

# Import core services
from . import payments
from . import database
from . import auth
from . import messaging

__all__ = [
    "market_engine",
    "consumer_voice", 
    "data_layer",
    "ai_insight",
    "report_builder",
    "location_intel",
    "knowledge_base",
    "business_os",
    "custom_research",
    "payments",
    "database",
    "auth",
    "messaging"
]
