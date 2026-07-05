from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# DB
from modules.database import Base, engine, get_db

# Routers - import the router variable from each router.py file
from modules.invoicing.router import router as invoicing_router
from modules.inventory.router import router as inventory_router
from modules.hr.router import router as hr_router
from modules.support.router import router as support_router
from modules.analytics.router import router as analytics_router
from modules.marketing.router import router as marketing_router
from modules.payments.router import router as payments_router
from modules.ai_agent.router import router as ai_agent_router

app = FastAPI(title="Business ERP API")


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


# Register all routers
app.include_router(invoicing_router)
app.include_router(inventory_router)
app.include_router(hr_router)
app.include_router(support_router)
app.include_router(analytics_router)
app.include_router(marketing_router)
app.include_router(payments_router)
app.include_router(ai_agent_router)


@app.get("/")
def root():
    return {"message": "Business ERP API is running", "docs": "/docs"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    return {"status": "ok"}
