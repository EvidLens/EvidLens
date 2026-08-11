import os
from supabase import create_client, Client
from fastapi import UploadFile
from sqlmodel import Session
import uuid

def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("APP_SUPABASE_KEY")
    print("DEBUG URL:", url)
    print("DEBUG KEY:", key[:10] if key else "NONE")
    return create_client(url, key)

BUCKET = "evidlens-files"

class StorageService:
    def __init__(self, db: Session):
        self.db = db
        self.supabase: Client = get_supabase_client()

    async def upload(self, file: UploadFile, folder: str = "uploads"):
        file_bytes = await file.read()
        filename = f"{folder}/{uuid.uuid4()}_{file.filename}"
        
        res = self.supabase.storage.from_(BUCKET).upload(
            path=filename,
            file=file_bytes,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )
        
        url_data = self.supabase.storage.from_(BUCKET).get_public_url(filename)
        return {"url": url_data, "path": filename}

    async def list_files(self, folder: str = "uploads"):
        res = self.supabase.storage.from_(BUCKET).list(folder)
        return res

    async def delete(self, file_id: str):
        res = self.supabase.storage.from_(BUCKET).remove([file_id])
        return res

async def upload_report_pdf(file_bytes, filename): # keep this if you use it elsewhere
    supabase = get_supabase_client()
    res = supabase.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"}
    )
    url_data = supabase.storage.from_(BUCKET).get_public_url(filename)
    return url_data
