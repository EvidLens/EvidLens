# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env first
load_dotenv()

from app.modules.database import init_db
from app.modules.seed_data import run_seed

# Import all 9 Lane Routers
from app.modules import (
    market_engine,
    consumer_voice,
    data_layer,
    ai_insight,
    report_builder,
    location_intel,
    knowledge_base,
    business_os,
    custom_research,
    payments,
    auth
)

app = FastAPI(
    title="EvidLens API",
    version="1.0.0",
    description="Kenya's Decision Intelligence Platform - 9 Lanes in 1"
)

# ======================
# CORS - For React + Vercel + Mobile
# ======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "https://evidlens.vercel.app",
        "*" # remove in prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# STARTUP EVENTS
# ======================
@app.on_event("startup")
def on_startup():
    print("Starting EvidLens...")
    init_db()  # Create all tables in Neon/SQlite
    run_seed() # Seed 47 Counties + 36 Sectors + FMCG. Zero Setup
    print("EvidLens Ready. All 9 Lanes loaded.")

# ======================
# HEALTH CHECK
# ======================
@app.get("/")
def root():
    return {
        "app": "EvidLens",
        "tagline": "Kenya's Decision Intelligence Platform",
        "version": "1.0.0",
        "lanes": 9,
        "status": "ok"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# ======================
# REGISTER ALL ROUTERS
# ======================
# Core Services
app.include_router(auth.router, prefix="/auth", tags=["Auth - Supabase"])
app.include_router(payments.router, prefix="/payments", tags=["Payments - M-Pesa"])

# 9 SAAS LANES
app.include_router(market_engine.router, prefix="/market", tags=["Lane 1: Market Insight Engine"])
app.include_router(consumer_voice.router, prefix="/voice", tags=["Lane 2: Consumer Voice Aggregator"])
app.include_router(data_layer.router, prefix="/data", tags=["Lane 3: Quantitative Data Layer"])
app.include_router(ai_insight.router, prefix="/ai", tags=["Lane 4: AI Insight Generator - Lens"])
app.include_router(report_builder.router, prefix="/reports", tags=["Lane 5: Report Builder - KRA PDF/Excel"])
app.include_router(location_intel.router, prefix="/location", tags=["Lane 6: Location Intelligence - Heatmaps"])
app.include_router(knowledge_base.router, prefix="/kb", tags=["Lane 7: Knowledge Base - 36 Sectors"])
app.include_router(business_os.router, prefix="/os", tags=["Lane 8: Business OS - ERP/CRM/HR"])
app.include_router(custom_research.router, prefix="/research", tags=["Lane 9: Custom Research Services"])

# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
