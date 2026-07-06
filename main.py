from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modules.database import Base, engine
import os

# Create FastAPI app
app = FastAPI(
    title="EvidLens - Kenya’s Decision Intelligence Platform",
    description="Consumer + Market Intelligence + Business OS for Kenya. 9 Lanes, 47 Counties, 36 Sectors",
    version="1.0.0"
)

# CORS for React + React Native + Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change to your Vercel domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables on startup
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    print("EvidLens DB tables created")

# Import all routers
from modules.auth.router import router as auth_router
from modules.market_engine.router import router as market_engine_router
from modules.consumer_voice.router import router as consumer_voice_router
from modules.data_layer.router import router as data_layer_router
from modules.ai_insights.router import router as ai_insights_router
from modules.report_builder.router import router as report_builder_router
from modules.location_intel.router import router as location_intel_router
from modules.knowledge_base.router import router as knowledge_base_router
from modules.business_os.router import router as business_os_router
from modules.payments.router import router as payments_router

# Include all 9 Lanes
app.include_router(auth_router, prefix="/auth", tags=["Auth - Supabase"])
app.include_router(market_engine_router, prefix="/market-engine", tags=["Lane 1: Market Insight Engine"])
app.include_router(consumer_voice_router, prefix="/consumer-voice", tags=["Lane 2: Consumer Voice Aggregator"])
app.include_router(data_layer_router, prefix="/data-layer", tags=["Lane 3: Data Layer"])
app.include_router(ai_insights_router, prefix="/ai-insights", tags=["Lane 4: AI Insight Generator - Lens"])
app.include_router(report_builder_router, prefix="/report-builder", tags=["Lane 5: Report Builder"])
app.include_router(location_intel_router, prefix="/location-intel", tags=["Lane 6: Location Intelligence"])
app.include_router(knowledge_base_router, prefix="/knowledge-base", tags=["Lane 7: Knowledge Base"])
app.include_router(business_os_router, prefix="/business-os", tags=["Lane 8: Business OS Core"])
app.include_router(payments_router, prefix="/payments", tags=["Payments - M-Pesa Daraja"])

# Root endpoints
@app.get("/")
def root(): 
    return {
        "message": "EvidLens API Running", 
        "version": "1.0.0", 
        "country": "Kenya",
        "tagline": "Kenya’s Decision Intelligence Platform"
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "EvidLens API"}

@app.get("/lanes")
def list_lanes():
    return {
        "lanes": [
            "Lane 1: Market Insight Engine",
            "Lane 2: Consumer Voice Aggregator", 
            "Lane 3: Data Layer",
            "Lane 4: AI Insight Generator",
            "Lane 5: Report Builder",
            "Lane 6: Location Intelligence",
            "Lane 7: Knowledge Base",
            "Lane 8: Business OS Core",
            "Lane 9: Custom Research Services"
        ]
    }
