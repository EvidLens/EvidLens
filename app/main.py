from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="EvidLens", debug=settings.DEBUG)

@app.get("/")
def read_root():
    return {"message": "EvidLens API is running", "debug": settings.DEBUG}

@app.get("/health")
def health_check():
    return {"status": "ok"}
