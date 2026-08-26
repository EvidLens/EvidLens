from typing import Dict, Any, Optional
from sqlmodel import Session, select, or_, func, desc
from datetime import datetime, timedelta, timezone

from app.core.models import KenyaLensBusiness, Deal, Funder, NewsArticle, SocialMention

UTC = timezone.utc

class CompetitiveEngineService:
    def __init__(self, db: Session):
        self.db = db

    async def company_deal_database(
        self, sector: str, county: Optional[str] = None, company_name: Optional[str] = None
    ) -> Dict[str, Any]:

        q = select(KenyaLensBusiness).where(KenyaLensBusiness.sector.ilike(f"%{sector}%"))

        if county:
            q = q.where(KenyaLensBusiness.county.ilike(f"%{county}%"))
        if company_name:
            q = q.where(KenyaLensBusiness.name.ilike(f"%{company_name}%"))

        companies = self.db.exec(q.order_by(desc(KenyaLensBusiness.id)).limit(100)).all()

        # Count deals per company
        deal_counts: Dict[str, int] = {}
        if companies:
            names = [c.name for c in companies]
            stmt = select(Deal.company_name, func.count(Deal.id)).where(
                Deal.company_name.in_(names)
            ).group_by(Deal.company_name)
            for name, cnt in self.db.exec(stmt).all():
                deal_counts[name] = cnt

        return {
            "sector": sector,
            "county": county,
            "total_found": len(companies),
            "companies": [
                {
                    "id": c.id,
                    "name": c.name,
                    "sector": c.sector,
                    "county": c.county,
                    "address": c.address,
                    "lat": c.lat,
                    "lng": c.lng,
                    "active_deals": deal_counts.get(c.name, 0),
                }
                for c in companies
            ],
        }

    async def funding_tracker(
        self, sector: str, county: Optional[str] = None,
        investor_name: Optional[str] = None, date_range: str = "90d"
    ) -> Dict[str, Any]:

        days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = days_map.get(date_range, 90)
        since = datetime.now(UTC) - timedelta(days=days)

        q = select(Deal).where(Deal.created_at >= since)

        if sector:
            q = q.where(
                or_(
                    Deal.title.ilike(f"%{sector}%"),
                    Deal.description.ilike(f"%{sector}%"),
                    Deal.company_name.ilike(f"%{sector}%"),
                )
            )
        if county:
            q = q.where(
                Deal.company_name.in_(
                    select(KenyaLensBusiness.name).where(
                        KenyaLensBusiness.county.ilike(f"%{county}%")
                    )
                )
            )
        if investor_name:
            q = q.where(
                Deal.funder_id.in_(
                    select(Funder.id).where(Funder.name.ilike(f"%{investor_name}%"))
                )
            )

        deals = self.db.exec(q.order_by(desc(Deal.created_at)).limit(100)).all()

        funder_ids = [d.funder_id for d in deals if d.funder_id]
        funders = {}
        if funder_ids:
            flist = self.db.exec(select(Funder).where(Funder.id.in_(funder_ids))).all()
            funders = {f.id: f for f in flist}

        total = sum(float(d.amount or 0) for d in deals)

        return {
            "sector": sector,
            "county": county,
            "date_range": date_range,
            "total_deals": len(deals),
            "total_funding_kes": total,
            "deals": [
                {
                    "id": d.id,
                    "company": d.company_name,
                    "amount": float(d.amount or 0),
                    "type": d.deal_type,
                    "stage": d.stage,
                    "status": d.status,
                    "funder": funders.get(d.funder_id).name if d.funder_id in funders else None,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in deals
            ],
        }

    async def digital_traffic_analyzer(self, competitor1: str, competitor2: str) -> Dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=30)

        c1_mentions = self.db.exec(
            select(func.count(SocialMention.id)).where(
                SocialMention.content.ilike(f"%{competitor1}%"),
                SocialMention.created_at >= since,
            )
        ).first() or 0

        c2_mentions = self.db.exec(
            select(func.count(SocialMention.id)).where(
                SocialMention.content.ilike(f"%{competitor2}%"),
                SocialMention.created_at >= since,
            )
        ).first() or 0

        c1_news = self.db.exec(
            select(func.count(NewsArticle.id)).where(
                NewsArticle.title.ilike(f"%{competitor1}%"),
                NewsArticle.published_at >= since,
            )
        ).first() or 0

        c2_news = self.db.exec(
            select(func.count(NewsArticle.id)).where(
                NewsArticle.title.ilike(f"%{competitor2}%"),
                NewsArticle.published_at >= since,
            )
        ).first() or 0

        return {
            "competitor1": competitor1,
            "competitor2": competitor2,
            "period": "last_30_days",
            "data_source": "EvidLens Social + News - REAL",
            "traffic_proxy": {
                competitor1: {
                    "social_mentions": int(c1_mentions),
                    "news_mentions": int(c1_news),
                    "visibility_score": int(c1_mentions) + int(c1_news),
                },
                competitor2: {
                    "social_mentions": int(c2_mentions),
                    "news_mentions": int(c2_news),
                    "visibility_score": int(c2_mentions) + int(c2_news),
                },
            },
        }

    async def competitor_monitor(self, competitor: str, signal_type: str) -> Dict[str, Any]:
        since = datetime.now(UTC) - timedelta(days=14)
        alerts = []

        if signal_type == "news":
            news = self.db.exec(
                select(NewsArticle)
               .where(NewsArticle.title.ilike(f"%{competitor}%"), NewsArticle.published_at >= since)
               .order_by(desc(NewsArticle.published_at))
               .limit(10)
            ).all()
            alerts = [
                {"type": "news", "title": n.title, "source": n.source, "url": n.url, "date": n.published_at.isoformat() if n.published_at else None}
                for n in news
            ]

        elif signal_type == "sentiment":
            social = self.db.exec(
                select(SocialMention)
               .where(SocialMention.content.ilike(f"%{competitor}%"), SocialMention.created_at >= since)
               .order_by(desc(SocialMention.created_at))
               .limit(20)
            ).all()
            alerts = [
                {"type": "social", "content": s.content, "platform": s.platform, "sentiment": s.sentiment, "date": s.created_at.isoformat() if s.created_at else None}
                for s in social
            ]

        elif signal_type == "funding":
            deals = self.db.exec(
                select(Deal)
               .where(Deal.company_name.ilike(f"%{competitor}%"), Deal.created_at >= since)
               .order_by(desc(Deal.created_at))
               .limit(5)
            ).all()
            alerts = [
                {"type": "funding", "amount": float(d.amount or 0), "stage": d.stage, "status": d.status, "date": d.created_at.isoformat() if d.created_at else None}
                for d in deals
            ]

        return {
            "competitor": competitor,
            "signal_type": signal_type,
            "period": "last_14_days",
            "alert_count": len(alerts),
            "alerts": alerts,
        }
