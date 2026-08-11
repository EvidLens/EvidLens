from fastapi import APIRouter, UploadFile, File, Depends
from sqlmodel import Session
from app.core.db import get_session
from app.modules.storage.service import StorageService

router = APIRouter(prefix="/storage", tags=["Storage"])

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), folder: str = "uploads", db: Session = Depends(get_session)):
    service = StorageService(db)
    return await service.upload(file, folder)

@router.get("/files")
async def list_files(folder: str = "uploads", db: Session = Depends(get_session)):
    service = StorageService(db)
    return await service.list_files(folder)

@router.delete("/files/{file_id}")
async def delete_file(file_id: str, db: Session = Depends(get_session)):
    service = StorageService(db)
    return await service.delete(file_id)
