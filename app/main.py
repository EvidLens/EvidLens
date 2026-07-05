from fastapi import FastAPI

app = FastAPI(title="EvidLens")

@app.get("/")
def read_root():
    return {"message": "EvidLens API is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
