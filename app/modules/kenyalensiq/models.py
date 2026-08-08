# app/modules/kenyalensiq/models.py
# PROXY ONLY - NO TABLE DEFINITIONS HERE AT ALL
from app.core.models import (
    KenyaLensSubscription,
    KenyaLensAlert, 
    KenyaLensMember,
    KenyaLensApiUsage,
    KenyaLensBusiness,
    KenyaLensSurvey,
    MarketMetric,
    SocialMention
)

__all__ = [
    "KenyaLensSubscription", "KenyaLensAlert", "KenyaLensMember", 
    "KenyaLensApiUsage", "KenyaLensBusiness", "KenyaLensSurvey", 
    "MarketMetric", "SocialMention"
]
