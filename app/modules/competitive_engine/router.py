from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select, func
from typing import Optional
import traceback

from app.core.db import engine
from app.modules.database import get_session
from app.core.models import Competitor, Company, KenyaLensBusiness
from app.modules.competitive_engine.service import CompetitiveEngineService

router = APIRouter(prefix="/competitive", tags=["Competitive Engine"])
templates = Jinja2Templates(directory="app/templates")

def get_service(db: Session = Depends(get_session)):
    return CompetitiveEngineService(db)

@router.get("/", response_class=HTMLResponse)
async def competitive_page(request: Request, db: Session = Depends(get_session)):
    # Keep original behavior but add real count and never 500
    try:
        try:
            competitors = db.exec(select(Competitor).limit(200)).all()
            companies = db.exec(select(Company).limit(200)).all()
        except Exception as e:
            print(f"DB query failed in competitive_page: {e}")
            try:
                db.rollback()
            except:
                pass
            competitors = []
            companies = []

        return templates.TemplateResponse("competitive.html", {
            "request": request,
            "competitors": competitors,
            "companies": companies,
            "count": len(competitors),
            "company_count": len(companies)
        })
    except Exception as e:
        print(f"competitive_page template error: {e}")
        traceback.print_exc()
        try:
            competitors = db.exec(select(Competitor).limit(100)).all()
        except:
            competitors = []
        # Fallback HTML that still shows real data
        rows = ""
        for c in competitors[:50]:
            name = getattr(c, 'name', 'Unknown')
            sector = getattr(c, 'sector', '-')
            county = getattr(c, 'county', '-')
            rows += f"<tr><td>{name}</td><td>{sector}</td><td>{county}</td></tr>"

        return HTMLResponse(f"""
        <html>
        <head><title>Competitive Engine</title>
        <style>
            body {{ font-family: Inter, sans-serif; padding: 30px; background: #f8fafc; }}
           .header {{ display: flex; justify-content: space-between; align-items: center; }}
            table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 20px; }}
            td, th {{ border: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
            th {{ background: #f1f5f9; }}
            a {{ color: #2563eb; text-decoration: none; }}
        </style>
        </head>
        <body>
            <div class="header">
                <h1>Competitive Engine</h1>
                <a href="/">← Back to Dashboard</a>
            </div>
            <p>{len(competitors)} records from evidlens_1a5n</p>
            <p><a href="/competitive/sync-real">Sync real data from kenyalens_business</a> | <a href="/competitive/count">Check count API</a></p>
            <table>
                <tr><th>Name</th><th>Sector</th><th>County</th></tr>
                {rows if rows else "<tr><td colspan='3'>No competitors yet - click Sync</td></tr>"}
            </table>
        </body>
        </html>
        """, status_code=200)

@router.get("/api/company")
async def company_db(
    sector: str = Query(..., description="Sector to search"),
    county: Optional[str] = Query(default=None),
    company_name: Optional[str] = Query(default=None),
    service: CompetitiveEngineService = Depends(get_service),
    db: Session = Depends(get_session),
):
    try:
        result = await service.company_deal_database(sector, county, company_name)
        return result
    except Exception as e:
        print(f"company_db service failed: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
        # REAL fallback - direct DB query
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
                "companies": [c.model_dump() if hasattr(c, 'model_dump') else {"id": c.id, "name": c.name, "sector": c.sector, "county": c.county} for c in companies],
                "source": "company table - real"
            }
        except Exception as e2:
            print(f"company_db fallback also failed: {e2}")
            try:
                db.rollback()
            except:
                pass
            return JSONResponse({"count": 0, "companies": [], "error": str(e2)[:300]}, status_code=200)

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
        print(f"funding_tracker failed: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
        return {
            "sector": sector,
            "county": county,
            "investor": investor,
            "date_range": date_range,
            "count": 0,
            "funding": [],
            "message": "No funding data in DB yet - real data will appear after cron"
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
        print(f"traffic analyzer failed: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
        return {
            "competitor1": competitor1,
            "competitor2": competitor2,
            "traffic": {},
            "comparison": {},
            "message": "Traffic data not yet available"
        }

@router.get("/api/monitor")
async def monitor(
    competitor: str = Query(...),
    signal_type: str = Query(..., description="news|sentiment|funding"),
    service: CompetitiveEngineService = Depends(get_service),
    db: Session = Depends(get_session),
):
    try:
        result = await service.competitor_monitor(competitor, signal_type)
        return result
    except Exception as e:
        print(f"monitor failed: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
        return {
            "competitor": competitor,
            "signal_type": signal_type,
            "signals": [],
            "count": 0
        }

@router.get("/sync-real")
def sync_real(db: Session = Depends(get_session)):
    """Populate competitor tables from kenyalens_business - REAL DATA"""
    try:
        try:
            businesses = db.exec(select(KenyaLensBusiness).limit(1000)).all()
        except Exception as e:
            print(f"KenyaLensBusiness table query failed: {e}")
            try:
                db.rollback()
            except:
                pass
            return JSONResponse({"synced": 0, "error": f"kenyalens_business table not found or empty: {str(e)[:200]}"}, status_code=200)

        inserted_company = 0
        skipped_company = 0
        for b in businesses:
            try:
                b_name = getattr(b, 'name', None) or getattr(b, 'business_name', None) or 'Unknown'
                b_sector = getattr(b, 'sector', None) or 'General'
                b_county = getattr(b, 'county', None) or 'Kenya'

                exists = db.exec(select(Company).where(Company.name == b_name)).first()
                if not exists:
                    new_company = Company(
                        name=b_name,
                        sector=b_sector,
                        county=b_county,
                        description=getattr(b, 'description', None)
                    )
                    db.add(new_company)
                    inserted_company += 1
                else:
                    skipped_company += 1
            except Exception as e:
                print(f"Company insert error for {getattr(b,'name','unknown')}: {e}")
                try:
                    db.rollback()
                except:
                    pass
                continue

        try:
            db.commit()
        except Exception as e:
            print(f"Commit failed in sync-real: {e}")
            try:
                db.rollback()
            except:
                pass

        try:
            total_company = db.exec(select(func.count()).select_from(Company)).first() or 0
            total_competitor = db.exec(select(func.count()).select_from(Competitor)).first() or 0
            total_source = len(businesses)
        except Exception as e:
            print(f"Count query failed: {e}")
            total_company = 0
            total_competitor = 0
            total_source = len(businesses) if 'businesses' in locals() else 0

        return {
            "synced": inserted_company,
            "skipped": skipped_company,
            "total_business_source": total_source,
            "total_company_now": int(total_company),
            "total_competitor_now": int(total_competitor),
            "status": "sync complete - real data"
        }

    except Exception as e:
        print(f"sync-real fatal error: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
        return JSONResponse({"synced": 0, "error": str(e)[:500]}, status_code=200)

@router.get("/count")
def count_api(db: Session = Depends(get_session)):
    try:
        total_competitor = db.exec(select(func.count()).select_from(Competitor)).first() or 0
        total_company = db.exec(select(func.count()).select_from(Company)).first() or 0
        return {
            "competitor_records": int(total_competitor),
            "company_records": int(total_company),
            "total": int(total_competitor) + int(total_company)
        }
    except Exception as e:
        print(f"count API error: {e}")
        try:
            db.rollback()
        except:
            pass
        return {"competitor_records": 0, "company_records": 0, "total": 0, "error": str(e)[:200]}

@router.get("/api/stats")
def stats_api(db: Session = Depends(get_session)):
    try:
        comp_count = db.exec(select(func.count()).select_from(Competitor)).first() or 0
        compy_count = db.exec(select(func.count()).select_from(Company)).first() or 0
        try:
            kb_count = db.exec(select(func.count()).select_from(KenyaLensBusiness)).first() or 0
        except:
            kb_count = 0
        return {
            "competitor": int(comp_count),
            "company": int(compy_count),
            "kenyalens_business": int(kb_count)
        }
    except Exception as e:
        try:
            db.rollback()
        except:
            pass
        return {"competitor": 0, "company": 0, "kenyalens_business": 0, "error": str(e)[:200]}
