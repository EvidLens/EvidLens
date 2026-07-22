from fastapi import APIRouter
from app.modules.kenyalensiq.router import router as lens_router

router = APIRouter()
router.include_router(lens_router, prefix="/kenyalensiq", tags=["KenyaLensIQ"])

__version__ = "2.0.0"
