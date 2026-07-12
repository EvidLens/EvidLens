from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.modules.market_engine.router import router as market_router
from app.modules.consumer_voice.router import router as consumer_router
from app.modules.data_layer.router import router as data_router
from app.modules.ai_insights.router import router as ai_router
from app.modules.report_builder.router import router as report_router
from app.modules.location_intel.router import router as location_router
from app.modules.knowledge_base.router import router as knowledge_router
from app.modules.business_os.router import router as business_router
from app.modules.auth.router import router as auth_router
from app.modules.payments.router import router as payments_router
from app.modules.web import routes as web_routes

app = FastAPI(
    title="EvidLens API",
    version="1.0.0",
    description="Kenya's Decision Intelligence Platform - 9 Lanes in 1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Commented out because folder doesn't exist yet
# from fastapi.staticfiles import StaticFiles
# app.mount("/static", StaticFiles(directory="app/modules/web/static"), name="static")

@app.get("/health")
def health():
    return {
        "app": "EvidLens",
        "tagline": "Kenya's Decision Intelligence Platform",
        "version": "1.0.0",
        "lanes": 9,
        "status": "ok"
    }

app.include_router(auth_router, prefix="/auth", tags=["Auth - Supabase"])
app.include_router(payments_router, prefix="/payments", tags=["Payments - M-Pesa"])
app.include_router(market_router, prefix="/market", tags=["Lane 1: Market Insight Engine"])
app.include_router(consumer_router, prefix="/voice", tags=["Lane 2: Consumer Voice Aggregator"])
app.include_router(data_router, prefix="/data", tags=["Lane 3: Quantitative Data Layer"])
app.include_router(ai_router, prefix="/ai", tags=["Lane 4: AI Insight Generator - Lens"])
app.include_router(report_router, prefix="/reports", tags=["Lane 5: Report Builder - KRA PDF/Excel"])
app.include_router(location_router, prefix="/location", tags=["Lane 6: Location Intelligence - Heatmaps"])
app.include_router(knowledge_router, prefix="/kb", tags=["Lane 7: Knowledge Base - 36 Sectors"])
app.include_router(business_router, prefix="/os", tags=["Lane 8: Business OS - ERP/CRM/HR"])

app.include_router(web_routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
