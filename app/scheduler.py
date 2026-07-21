from app.modules.database import MarketMetric, PriceData, NewsArticle, SocialMention
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from sqlmodel import Session, select, func
from app.modules.database import engine

scheduler = BackgroundScheduler()

scheduler = BackgroundScheduler()

def update_demand_scores():
    """Runs every 1 hour. Calculates realtime demand_score"""
    with Session(engine) as session:
        print(f"[{datetime.now()}] Running demand score update...")
        
        # Get all unique product + county combos from last 24h
        products = session.exec(select(PriceData.product_name).distinct()).all()
        counties = session.exec(select(PriceData.county).distinct()).all()

        for product in products:
            for county in counties:
                score = 0
                
                # 1. Price spike factor: +40 if price jumped >10% in 24h
                price_data = session.exec(
                    select(PriceData).where(PriceData.product_name==product, PriceData.county==county)
                   .order_by(PriceData.timestamp.desc()).limit(2)
                ).all()
                if len(price_data) == 2:
                    change = (price_data[0].price - price_data[1].price) / price_data[1].price
                    if change > 0.1: score += 40

                # 2. News factor: +30 per news article in last 24h
                news_count = session.exec(
                    select(func.count()).select_from(NewsArticle)
                   .where(NewsArticle.product==product, NewsArticle.timestamp > func.now() - "1 day")
                ).one()
                score += news_count * 30

                # 3. Social factor: +10 per 100 mentions in last 24h
                social_count = session.exec(
                    select(func.count()).select_from(SocialMention)
                   .where(SocialMention.product==product, SocialMention.timestamp > func.now() - "1 day")
                ).one()
                score += (social_count // 100) * 10

                # Upsert into MarketMetric
                metric = session.exec(
                    select(MarketMetric).where(MarketMetric.product_name==product, MarketMetric.county==county)
                ).first()
                
                if metric:
                    metric.demand_score = score
                    metric.updated_at = datetime.utcnow()
                else:
                    metric = MarketMetric(
                        product_name=product, county=county, demand_score=score,
                        sector="Agriculture", updated_at=datetime.utcnow() # change sector if you have it
                    )
                    session.add(metric)
        
        session.commit()
        print(f"[{datetime.now()}] Demand scores updated")

# Schedule it: every 1 hour
scheduler.add_job(update_demand_scores, 'interval', hours=1, id='demand_score_job')
scheduler.start()

print("EvidLens Scheduler started: Demand[1h] Price[Mon 3AM] News[6h] Social[1h]")
