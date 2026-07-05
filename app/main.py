from fastapi import FastAPI
from app.core.config import settings
from app.core.db import engine, Base

app = FastAPI(title="EvidLens", debug=settings.DEBUG)

# Create tables on startup
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "EvidLens API is running", "debug": settings.DEBUG}

@app.get("/health")
def health_check():
    return {"status": "ok"}
