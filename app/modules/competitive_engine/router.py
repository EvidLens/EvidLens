from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select, func
from typing import Optional
import logging

from app.core.db import get_session
from app.core.models import Competitor, Company, KenyaLensBusiness
from app.modules.competitive_engine.service import CompetitiveEngineService

router = APIRouter(prefix="/competitive", tags=["Competitive Engine"])
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("evidlens.competitive")

def get_service(db: Session = Depends(get_session)):
    return CompetitiveEngineService(db)

async def _get_user(request: Request, db: Session):
    try:
        from app.modules.auth.dependencies import get_current_user
        return await get_current_user(request, db)
    except Exception:
        return None

def _clean_rating(value):
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if v <= 0:
        return None
    if v > 5:
        return 5.0
    return round(v, 1)

def _threat_level(sector, county, rating):
    text = f"{sector or ''} {county or ''}".lower()
    if any(k in text for k in ["telecom", "banking", "fintech", "insurance"]):
        return "High"
    if any(k in text for k in ["retail", "agriculture", "manufacturing", "energy"]):
        return "Medium"
    return "Low"

def _normalize_company(c):
    rating = _clean_rating(getattr(c, "rating", None))
    sector = getattr(c, "sector", "") or "General"
    county = getattr(c, "county", "") or "Kenya"
    return {
        "id": getattr(c, "id", None),
        "name": getattr(c, "name", "Unknown") or "Unknown",
        "sector": sector,
        "county": county,
        "description": getattr(c, "description", "") or "",
        "rating": rating,
        "avg_rating": rating,
        "threat": _threat_level(sector, county, rating),
        "threat_level": _threat_level(sector, county, rating),
    }

def _normalize_competitor(c):
    rating = _clean_rating(getattr(c, "rating", None))
    sector = getattr(c, "sector", "") or "General"
    county = getattr(c, "county", "") or "Kenya"
    return {
        "id": getattr(c, "id", None),
        "name": getattr(c, "name", "Unknown") or "Unknown",
        "sector": sector,
        "county": county,
        "description": getattr(c, "description", "") or "",
        "rating": rating,
        "avg_rating": rating,
        "threat": _threat_level(sector, county, rating),
        "threat_level": _threat_level(sector, county, rating),
    }

@router.get("/", response_class=HTMLResponse)
async def competitive_page(request: Request, db: Session = Depends(get_session)):
    try:
        competitors_raw = db.exec(select(Competitor).limit(200)).all()
        companies_raw = db.exec(select(Company).limit(200)).all()
    except Exception as e:
        logger.exception(f"competitive_page DB failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        competitors_raw = []
        companies_raw = []

    competitors = [_normalize_competitor(c) for c in competitors_raw]
    companies = [_normalize_company(c) for c in companies_raw]
    all_items = competitors + companies
    rated = [x for x in all_items if x["rating"] is not None]
    avg_rating = round(sum(x["rating"] for x in rated) / len(rated), 1) if rated else None
    high_threat = len([x for x in all_items if x["threat"] == "High"])

    current_user = await _get_user(request, db)
    return templates.TemplateResponse("competitive.html", {
        "request": request,
        "competitors": competitors,
        "companies": companies,
        "items": all_items,
        "count": len(competitors),
        "company_count": len(companies),
        "total_count": len(all_items),
        "avg_rating": avg_rating,
        "high_threat_count": high_threat,
        "has_data": len(all_items) > 0,
        "current_user": current_user,
        "user": current_user,
    })

@router.get("/api/company")
async def company_db(
    sector: str = Query(...),
    county: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    service: CompetitiveEngineService = Depends(get_service),
    db: Session = Depends(get_session),
):
    try:
        result = await service.company_deal_database(sector, county, company_name)
        return result
    except Exception as e:
        logger.exception(f"company_db service failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        try:
            q = select(Company)
            if sector:
                q = q.where(Company.sector == sector)
            if county:
                q = q.where(Company.county == county)
            if company_name:
                q = q.where(Company.name.ilike(f"%{company_name}%"))
            companies = db.exec(q.limit(200)).all()
            return {
                "sector": sector,
                "county": county,
                "company_name": company_name,
                "count": len(companies),
                "companies": [_normalize_company(c) for c in companies],
                "source": "Company Directory",
            }
        except Exception as e2:
            logger.exception(f"company_db fallback failed: {e2}")
            try:
                db.rollback()
            except Exception:
                pass
            return JSONResponse({"count": 0, "companies": []}, status_code=200)

@router.get("/api/funding")
async def funding(
    sector: str = Query(...),
    county: Optional[str] = Query(default=None),
    investor: Optional[str] = Query(default=None),
    date_range: str = Query(default="90d"),
    service: CompetitiveEngineService = Depends(get_service),
    db: Session = Depends(get_session),
):
    try:
        result = await service.funding_tracker(sector, county, investor, date_range)
        return result
    except Exception as e:
        logger.exception(f"funding_tracker failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "sector": sector,
            "county": county,
            "investor": investor,
            "date_range": date_range,
            "count": 0,
            "funding": [],
            "message": "No funding data yet",
        }

@router.get("/api/traffic")
async def traffic(
    competitor1: str = Query(...),
    competitor2: str = Query(...),
    service: CompetitiveEngineService = Depends(get_service),
    db: Session = Depends(get_session),
):
    try:
        result = await service.digital_traffic_analyzer(competitor1, competitor2)
        return result
    except Exception as e:
        logger.exception(f"traffic analyzer failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "competitor1": competitor1,
            "competitor2": competitor2,
            "traffic": {},
            "comparison": {},
            "message": "Traffic data not yet available",
        }

@router.get("/api/monitor")
async def monitor(
    competitor: str = Query(...),
    signal_type: str = Query(...),
    service: CompetitiveEngineService = Depends(get_service),
    db: Session = Depends(get_session),
):
    try:
        result = await service.competitor_monitor(competitor, signal_type)
        return result
    except Exception as e:
        logger.exception(f"monitor failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "competitor": competitor,
            "signal_type": signal_type,
            "signals": [],
            "count": 0,
        }

@router.get("/sync-real")
def sync_real(db: Session = Depends(get_session)):
    try:
        try:
            businesses = db.exec(select(KenyaLensBusiness).limit(1000)).all()
        except Exception as e:
            logger.exception(f"KenyaLensBusiness query failed: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return JSONResponse({"synced": 0, "error": "Business directory not available"}, status_code=200)

        inserted_company = 0
        skipped_company = 0
        for b in businesses:
            try:
                b_name = getattr(b, "name", None) or getattr(b, "business_name", None) or "Unknown"
                b_sector = getattr(b, "sector", None) or "General"
                b_county = getattr(b, "county", None) or "Kenya"
                exists = db.exec(select(Company).where(Company.name == b_name)).first()
                if not exists:
                    new_company = Company(
                        name=b_name,
                        sector=b_sector,
                        county=b_county,
                        description=getattr(b, "description", None),
                    )
                    db.add(new_company)
                    inserted_company += 1
                else:
                    skipped_company += 1
            except Exception as e:
                logger.exception(f"Company insert failed: {e}")
                try:
                    db.rollback()
                except Exception:
                    pass
                continue

        try:
            db.commit()
        except Exception as e:
            logger.exception(f"Commit failed in sync-real: {e}")
            try:
                db.rollback()
            except Exception:
                pass

        try:
            total_company = db.exec(select(func.count()).select_from(Company)).first() or 0
            total_competitor = db.exec(select(func.count()).select_from(Competitor)).first() or 0
            total_source = len(businesses)
        except Exception as e:
            logger.exception(f"Count query failed: {e}")
            total_company = 0
            total_competitor = 0
            total_source = len(businesses)

        return {
            "synced": inserted_company,
            "skipped": skipped_company,
            "total_business_source": total_source,
            "total_company_now": int(total_company),
            "total_competitor_now": int(total_competitor),
            "status": "sync complete",
        }
    except Exception as e:
        logger.exception(f"sync-real fatal: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return JSONResponse({"synced": 0, "error": "Sync failed. Please try again."}, status_code=200)

@router.get("/count")
def count_api(db: Session = Depends(get_session)):
    try:
        total_competitor = db.exec(select(func.count()).select_from(Competitor)).first() or 0
        total_company = db.exec(select(func.count()).select_from(Company)).first() or 0
        return {
            "competitor_records": int(total_competitor),
            "company_records": int(total_company),
            "total": int(total_competitor) + int(total_company),
        }
    except Exception as e:
        logger.exception(f"count API error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {"competitor_records": 0, "company_records": 0, "total": 0}

@router.get("/api/stats")
def stats_api(db: Session = Depends(get_session)):
    try:
        comp_count = db.exec(select(func.count()).select_from(Competitor)).first() or 0
        compy_count = db.exec(select(func.count()).select_from(Company)).first() or 0
        try:
            kb_count = db.exec(select(func.count()).select_from(KenyaLensBusiness)).first() or 0
        except Exception:
            kb_count = 0
        return {
            "competitor": int(comp_count),
            "company": int(compy_count),
            "kenyalens_business": int(kb_count),
        }
    except Exception as e:
        logger.exception(f"stats API error: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return {"competitor": 0, "company": 0, "kenyalens_business": 0}
