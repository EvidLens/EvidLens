"""
EvidLens Core Modules
Kenya's Decision Intelligence Platform
"""

__version__ = "1.0.0"

# Only import core services here. Don't import messaging to avoid circular import
from . import database
from . import auth
from . import payments

__all__ = [
    "database",
    "auth", 
    "payments"
]
