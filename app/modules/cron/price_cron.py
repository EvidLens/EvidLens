from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.modules.database import SessionLocal
from app.modules.data_layer.service import fetch_price_trends

scheduler = AsyncIOScheduler()

def run_price_job():
    db = SessionLocal()
    try:
        count = fetch_price_trends(db)
        print(f"Price cron completed. {count} products updated")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(run_price_job, 'cron', day_of_week='mon', hour=3, minute=0) # Mon 3AM
        scheduler.start()
        print("Price Scheduler started")
