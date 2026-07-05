from fastapi import FastAPI
from app.core.config import settings
from app.core.db import engine, Base
from app.modules.auth import router as auth_router
from app.modules.crm.router import router as crm_router

app = FastAPI(title="EvidLens", debug=settings.DEBUG)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(crm_router)

@app.get("/")
def read_root():
    return {"message": "EvidLens API is running", "debug": settings.DEBUG}

@app.get("/health")
def health_check():
    return {"status": "ok"}
    return {"status": "ok"}
