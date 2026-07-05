from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import engine, Base

# Import all module routers
from app.modules.invoicing import router as invoicing_router
from app.modules.inventory import router as inventory_router
from app.modules.hr import router as hr_router
from app.modules.support import router as support_router
from app.modules.analytic import router as analytic_router
from app.modules.marketing import router as marketing_router
from app.modules.payments import router as payments_router
from app.modules.ai_agent import router as ai_agent_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Business ERP API",
    description="A-Z Business Management System",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(invoicing_router.router)
app.include_router(inventory_router.router)
app.include_router(hr_router.router)
app.include_router(support_router.router)
app.include_router(analytic_router.router)
app.include_router(marketing_router.router)
app.include_router(payments_router.router)
app.include_router(ai_agent_router.router)

@app.get("/")
def root():
    return {"message": "Business ERP API is running", "docs": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
