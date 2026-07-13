from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os

load_dotenv()

from app.modules.db import init_db
from app.modules.cron.price_cron import start_scheduler

# Import all models so tables are created
from app.modules.auth.models import User, UserRole
from app.modules.models import Sector, County, CoreProduct
from app.modules.payments.models import Payment, Subscription, MpesaTransaction
from app.modules.report_builder.models import Report, ReportTemplate, ReportShare
from app.modules.market_engine.models import MarketSearch, Competitor, MarketMetric

# Import all routers
from app.modules.auth.router import router as auth_router
from app.modules.payments.router import router as payments_router
from app.modules.market_engine.router import router as market_router
from app.modules.consumer_voice.router import router as consumer_router
from app.modules.data_layer.router import router as data_router
from app.modules.ai_insights.router import router as ai_router
from app.modules.report_builder.router import router as report_router
from app.modules.location_intel.router import router as location_router
from app.modules.knowledge_base.router import router as knowledge_router
from app.modules.business_os.router import router as business_router
from app.modules.rag.router import router as rag_router
from app.modules.web import routes as web_routes

app = FastAPI(
    title="EvidLens API", 
    version="1.0.0", 
    description="Kenya's Decision Intelligence Platform - 9 Lanes in 1. All 35 Sectors."
)

@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", auto_reload=True)

@app.exception_handler(500)
async def internal_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0", "sectors": 35}

# API Routers
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(payments_router, prefix="/payments", tags=["Payments"])
app.include_router(market_router, prefix="/market", tags=["Market Engine"])
app.include_router(consumer_router, prefix="/voice", tags=["Consumer Voice"])
app.include_router(data_router, prefix="/data", tags=["Data Layer"])
app.include_router(ai_router, prefix="/ai", tags=["AI Insights"])
app.include_router(report_router, prefix="/reports", tags=["Report Builder"])
app.include_router(location_router, prefix="/location", tags=["Location Intel"])
app.include_router(knowledge_router, prefix="/kb", tags=["Knowledge Base"])
app.include_router(business_router, prefix="/os", tags=["Business OS"])
app.include_router(rag_router, prefix="/api", tags=["RAG"])

# Web UI Routes - NO PREFIX
app.include_router(web_routes.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
