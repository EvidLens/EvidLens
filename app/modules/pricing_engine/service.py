from sqlmodel import Session, select, func, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from app.modules.pricing_engine.models import ProductPrice, RetailOutlet, Competitor
from app.core.models import MarketMetric, MarketSearch

UTC = timezone.utc

def search_market(db: Session, q: str, sector: str, county: str) -> Dict[str, Any]:
    # LOG SEARCH - REAL
    db.add(MarketSearch(query=q, sector=sector, county=county))
    db.commit()

    # REAL METRICS FROM MarketMetric
    metrics = db.exec(select(MarketMetric).where(MarketMetric.sector.ilike(f"%{sector}%"), MarketMetric.county.ilike(f"%{county}%"))).all()
    competitors = db.exec(select(Competitor).where(Competitor.sector.ilike(f"%{sector}%"), Competitor.county.ilike(f"%{county}%")).limit(10)).all()

    prices = [m.avg_price_kes for m in metrics if m.avg_price_kes]
    demand_scores = [m.demand_score for m in metrics if m.demand_score]
    avg_demand = round(sum(demand_scores)/len(demand_scores), 2) if demand_scores else 0

    return {
        "query": q,
        "sector": sector,
        "county": county,
        "currency": "KES",
        "demand_level": "High" if avg_demand > 7 else "Medium" if avg_demand > 4 else "Low",
        "demand_score": avg_demand,
        "price_range": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
            "avg": round(sum(prices)/len(prices), 2) if prices else 0,
        },
        "data_points": len(metrics),
        "competitors": [{"name": c.name, "lat": c.lat, "lng": c.lng} for c in competitors],
        "competitor_count": len(competitors),
    }

def get_price_oracle_data(db: Session, product: str, county: Optional[str] = None) -> Dict[str, Any]:
    q = select(ProductPrice).where(ProductPrice.product_name.ilike(f"%{product}%"))
    if county:
        q = q.where(ProductPrice.county.ilike(f"%{county}%"))

    points = db.exec(q.order_by(desc(ProductPrice.created_at)).limit(200)).all()

    # Fallback to MarketMetric if ProductPrice empty
    if not points:
        m_q = select(MarketMetric).where(MarketMetric.product.ilike(f"%{product}%"))
        if county:
            m_q = m_q.where(MarketMetric.county.ilike(f"%{county}%"))
        metrics = db.exec(m_q.limit(200)).all()
        data = [{"price": float(m.avg_price_kes or 0), "county": m.county, "date": m.created_at.isoformat() if hasattr(m, 'created_at') else None} for m in metrics]
        points_count = len(metrics)
    else:
        data = [{"price": p.price_kes, "county": p.county, "brand": p.brand, "date": p.created_at.isoformat()} for p in points]
        points_count = len(points)

    prices_only = [d["price"] for d in data if d["price"]]
    avg = sum(prices_only)/len(prices_only) if prices_only else 0

    return {
        "product": product,
        "county": county,
        "count": points_count,
        "avg_kes": round(avg,2),
        "min_kes": min(prices_only) if prices_only else 0,
        "max_kes": max(prices_only) if prices_only else 0,
        "history": data[:100],
        "recommended_price": round(avg * 1.2, 2), # 20% margin
    }

def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    price_count = db.exec(select(func.count(ProductPrice.id))).first() or 0
    outlet_count = db.exec(select(func.count(RetailOutlet.id))).first() or 0
    comp_count = db.exec(select(func.count(Competitor.id))).first() or 0
    search_count = db.exec(select(func.count(MarketSearch.id))).first() or 0
    metric_count = db.exec(select(func.count(MarketMetric.id))).first() or 0

    return {
        "price_count": price_count,
        "outlet_count": outlet_count,
        "competitor_count": comp_count,
        "search_count": search_count,
        "metric_count": metric_count,
        "total_records": price_count + metric_count,
    }
