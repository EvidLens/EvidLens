from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import threading # ADD THIS

# Load env first
load_dotenv()

from app.modules.db import init_db
from app.modules.seed_data import run_seed

# Import all 9 Lane Routers DIRECTLY - don't go through app.modules
from app.modules.market_engine.router import router as market_router
from app.modules.consumer_voice.router import router as consumer_router
from app.modules.data_layer.router import router as data_router
from app.modules.ai_insights.router import router as ai_router
from app.modules.report_builder.router import router as report_router
from app.modules.location_intel.router import router as location_router
from app.modules.knowledge_base.router import router as knowledge_router
from app.modules.business_os.router import router as business_router
# from app.modules.custom_research.router import router as research_router
from app.modules.auth.router import router as auth_router
from app.modules.payments.router import router as payments_router

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
# STARTUP EVENTS - RUN IN BACKGROUND
# ======================
def run_seed_in_background():
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
app.include_router(auth_router, prefix="/auth", tags=["Auth - Supabase"])
app.include_router(payments_router, prefix="/payments", tags=["Payments - M-Pesa"])

# 9 SAAS LANES
app.include_router(market_router, prefix="/market", tags=["Lane 1: Market Insight Engine"])
app.include_router(consumer_router, prefix="/voice", tags=["Lane 2: Consumer Voice Aggregator"])
app.include_router(data_router, prefix="/data", tags=["Lane 3: Quantitative Data Layer"])
app.include_router(ai_router, prefix="/ai", tags=["Lane 4: AI Insight Generator - Lens"])
app.include_router(report_router, prefix="/reports", tags=["Lane 5: Report Builder - KRA PDF/Excel"])
app.include_router(location_router, prefix="/location", tags=["Lane 6: Location Intelligence - Heatmaps"])
app.include_router(knowledge_router, prefix="/kb", tags=["Lane 7: Knowledge Base - 36 Sectors"])
app.include_router(business_router, prefix="/os", tags=["Lane 8: Business OS - ERP/CRM/HR"])

# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
