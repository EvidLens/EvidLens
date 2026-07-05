from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.db import engine, Base  # FIXED: removed "app."

# Import all module routers
from modules.invoicing import router as invoicing_router
from modules.inventory import router as inventory_router
from modules.hr import router as hr_router
from modules.support import router as support_router
from modules.analytic import router as analytic_router
from modules.marketing import router as marketing_router
from modules.payments import router as payments_router
from modules.ai_agent import router as ai_agent_router


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

# Create tables on startup
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


# Register all routers
app.include_router(invoicing_router)
app.include_router(inventory_router)
app.include_router(hr_router)
app.include_router(support_router)
app.include_router(analytic_router)
app.include_router(marketing_router)
app.include_router(payments_router)
app.include_router(ai_agent_router)


@app.get("/")
def root():
    return {"message": "Business ERP API is running", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
