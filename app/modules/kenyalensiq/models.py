# app/modules/kenyalensiq/models.py
from app.core.models import (
    KenyaLensSubscription,
    KenyaLensAlert, 
    KenyaLensMember,
    KenyaLensApiUsage,
    KenyaLensBusiness,
    KenyaLensSurvey,
    MarketMetric,
    SocialMention,
    NewsArticle  # ADD THIS
)

__all__ = [
    "KenyaLensSubscription", "KenyaLensAlert", "KenyaLensMember", 
    "KenyaLensApiUsage", "KenyaLensBusiness", "KenyaLensSurvey", 
    "MarketMetric", "SocialMention", "NewsArticle"
]
