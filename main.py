from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
from app.modules.models import init_db

app = FastAPI(
    title="EvidLens API",
    version="1.0.0",
    description="Kenya's Decision Intelligence Platform - 9 Lanes in 1"
)

# Create tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change to ["https://your-vercel-app.vercel.app"] later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates") # <-- ADDED THIS

@app.get("/health")
def health():
    return {"status": "healthy", "db": "connected"}

# Include all 9 lanes
app.include_router(auth_router, prefix="/auth")
app.include_router(payments_router, prefix="/payments")
app.include_router(market_router, prefix="/market")
app.include_router(consumer_router, prefix="/voice")
app.include_router(data_router, prefix="/data")
app.include_router(ai_router, prefix="/ai")
app.include_router(report_router, prefix="/reports")
app.include_router(location_router, prefix="/location")
app.include_router(knowledge_router, prefix="/kb")
app.include_router(business_router, prefix="/os")
app.include_router(web_routes.router) # dashboard routes

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
