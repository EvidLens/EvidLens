from app.modules.database import MarketMetric, PriceData, NewsArticle, SocialMention, engine
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from sqlmodel import Session, select, func

scheduler = BackgroundScheduler()

def update_demand_scores():
    with Session(engine) as session:
        print(f"[{datetime.now()}] Running demand score update...")
        yesterday = datetime.utcnow() - timedelta(days=1)

        rows = session.exec(select(PriceData.product_name, PriceData.county, PriceData.sector).distinct()).all()

        for product, county, sector in rows:
            score = 0

            price_data = session.exec(
                select(PriceData).where(PriceData.product_name==product, PriceData.county==county)
             .order_by(PriceData.timestamp.desc()).limit(2)
            ).all()
            if len(price_data) == 2:
                change = (price_data[0].price - price_data[1].price) / price_data[1].price
                if change > 0.1: score += 40

            news_count = session.exec(
                select(func.count()).select_from(NewsArticle)
             .where(NewsArticle.product==product, NewsArticle.timestamp > yesterday)
            ).one()
            score += news_count * 30

            social_count = session.exec(
                select(func.count()).select_from(SocialMention)
             .where(SocialMention.product==product, SocialMention.timestamp > yesterday)
            ).one()
            score += (social_count // 100) * 10

            metric = session.exec(
                select(MarketMetric).where(MarketMetric.product==product, MarketMetric.county==county)
            ).first()

            if metric:
                metric.demand_score = score
                metric.sector = sector
                metric.timestamp = datetime.utcnow()
            else:
                metric = MarketMetric(
                    product=product, county=county, sector=sector, demand_score=score, timestamp=datetime.utcnow()
                )
                session.add(metric)

        session.commit()
        print(f"[{datetime.now()}] Demand scores updated")

scheduler.add_job(update_demand_scores, 'interval', hours=1, id='demand_score_job')
scheduler.start()

print("EvidLens Scheduler started: Demand[1h] Price[Mon 3AM] News[6h] Social[1h]")
