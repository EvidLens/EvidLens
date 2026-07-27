scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)
app = FastAPI(title="EvidLens API", version="2.5.12")

def safe_job(job_func, job_name):
    """Wrapper so 1 job failing doesn't kill others"""
    try:
        print(f"[{job_name}] Running...")
        job_func()
        print(f"[{job_name}] Success")
    except Exception as e:
        print(f"[{job_name}] FAILED: {e}")
        traceback.print_exc()

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    print("DB tables checked/created")

    # Jobs
    scheduler.add_job(
        lambda: safe_job(scrape_kpin_prices, "KPIN"),
        CronTrigger(hour=settings.KPIN_SCRAPE_HOUR, minute=settings.KPIN_SCRAPE_MINUTE),
        id="kpin_scrape", replace_existing=True
    )
    scheduler.add_job(
        lambda: safe_job(fetch_real_news, "NEWS"),
        CronTrigger(hour=settings.NEWS_SCRAPE_HOUR, minute=settings.NEWS_SCRAPE_MINUTE),
        id="news_scrape", replace_existing=True
    )
    scheduler.add_job(
        lambda: safe_job(fetch_real_tweets, "TWEETS"),
        CronTrigger(hour=settings.TWEETS_SCRAPE_HOUR, minute=settings.TWEETS_SCRAPE_MINUTE),
        id="tweets_scrape", replace_existing=True
    )
    scheduler.start()
    print(f"Scheduler started. Timezone: {settings.SCHEDULER_TIMEZONE}")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("Scheduler shut down")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True

   # ====== SCHEDULER + DB INIT ======
scheduler = BackgroundScheduler()

def init_db():
    SQLModel.metadata.create_all(engine)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def seed_data():
    with Session(engine) as session:
        if session.exec(select(func.count(KenyaLensBusiness.id))).one() == 0:
            session.add_all([
                KenyaLensBusiness(name="Safaricom PLC", sector="Telecom", county="Nairobi"),
                KenyaLensBusiness(name="KCB Bank", sector="Banking", county="Nairobi"),
                KenyaLensBusiness(name="Equity Bank", sector="Banking", county="Nairobi"),
            ])
            session.commit()

def start_scheduler():
    print("Scheduler started")

def check_subscription(user_id, db):
    return True # placeholder

def generate_insights(message):
    return f"AI Insight: Demand for '{message}' is rising in Nairobi. Consider stocking."

def log_query(db, user_id):
    pass

def apply_sort(query, model, sort_by, order):
    column = getattr(model, sort_by, model.id)
    if order == "desc":
        return query.order_by(desc(column))
    return query.order_by(column)

@app.on_event("startup")
def on_startup():
    init_db()
    create_db_and_tables()
    seed_data()
    start_scheduler()
    scheduler.add_job(scrape_kpin_prices, "cron", hour="0,6,12,18")
    scheduler.add_job(fetch_real_news, "interval", hours=6)
    scheduler.add_job(fetch_real_tweets, "interval", hours=3)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
                         
