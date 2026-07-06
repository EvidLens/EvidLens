from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modules.database import Base, engine

app = FastAPI(
    title="EvidLens",
    description="Kenya’s Decision Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

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

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(market_engine_router, prefix="/market-engine", tags=["Lane1"])
app.include_router(consumer_voice_router, prefix="/consumer-voice", tags=["Lane2"])
app.include_router(data_layer_router, prefix="/data-layer", tags=["Lane3"])
app.include_router(ai_insights_router, prefix="/ai-insights", tags=["Lane4"])
app.include_router(report_builder_router, prefix="/report-builder", tags=["Lane5"])
app.include_router(location_intel_router, prefix="/location-intel", tags=["Lane6"])
app.include_router(knowledge_base_router, prefix="/knowledge-base", tags=["Lane7"])
app.include_router(business_os_router, prefix="/business-os", tags=["Lane8"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])

@app.get("/")
def root():
    return {"message": "EvidLens API Running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

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
