from sqlalchemy.orm import Session
from typing import Dict, Any, List
import httpx
import os
import json

from app.modules.knowledge_base.service import get_sector_benchmark
from app.modules.data_layer.service import get_aggregated_prices

GROQ_KEY = os.getenv("GROQ_API_KEY")

def run_rag_pipeline(db: Session, query: str, sector: str, county: str) -> Dict[str, Any]:
    """
    RAG Pipeline: Retrieve sector/county/price data -> Generate with Groq
    No product names or brands are sent to AI. Only aggregates.
    """
    # 1. RETRIEVE - Pull context from our own DB
    benchmark = get_sector_benchmark(sector)
    county_obj = get_county_by_name(county)
    price_stats = get_aggregated_prices(db, sector)
    
    county_name = county_obj["name"] if county_obj else county
    
    # Basic market size calc: population * penetration * avg_price
    population = 50_000_000 # Replace with county pop later
    est_market_size = population * benchmark["penetration_rate"] * price_stats["avg"]
    
    context = {
        "sector": sector,
        "county": county_name,
        "avg_margin_percent": benchmark["avg_margin_percent"],
        "penetration_rate_percent": benchmark["penetration_rate"] * 100,
        "avg_price_kes": price_stats["avg"],
        "price_range_kes": f"{price_stats['min']} - {price_stats['max']}",
        "estimated_market_size_kes": est_market_size,
        "regulatory_body": benchmark["regulatory_body"]
    }
    
    # 2. GENERATE - Call Groq or fallback to template
    system_prompt = """You are EvidLens, a Kenya Decision Intelligence AI. 
    Use ONLY the provided context. Be factual, KRA-compliant, no brand names.
    Output 6 sections: Executive Summary, Market Size, Risks, Competitors, Financials, Recommendation."""
    
    user_prompt = f"Context: {json.dumps(context, indent=2)}\n\nUser Query: {query}\n\nGenerate report."
    
    # Fallback answer if no GROQ key
    answer = f"""**Executive Summary**: {query} in the {sector} sector, {county_name} County shows moderate potential.
**Market Size**: Estimated KES {est_market_size:,.0f} based on {benchmark['penetration_rate']*100}% penetration.
**Risks**: High competition, regulatory compliance with {benchmark['regulatory_body']}.
**Competitors**: {price_stats['count']} tracked players in this category.
**Financials**: Avg price KES {price_stats['avg']:,.0f}. Avg margin {benchmark['avg_margin_percent']}%.
**Recommendation**: PROCEED WITH CAUTION. Validate with ground survey."""
    
    sources = ["kenya_sectors.json", "kenya_counties.json", "fmcg_catalog.json", "KNBS"]
    confidence = 0.72
    
    if GROQ_KEY:
        try:
            res = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 900
                },
                timeout=30
            )
            answer = res.json()["choices"][0]["message"]["content"]
            confidence = 0.88
        except Exception as e:
            print(f"Groq Error: {e}") # keep fallback
    
    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence
    }

def generate_insights(query: str, market_dict: dict) -> str:
    """Wrapper for reports.service.py compatibility"""
    result = run_rag_pipeline(None, query, market_dict["sector"], market_dict["location"])
    
    recommendation = "PROCEED" if "PROCEED" in result["answer"] else "REVIEW"
    
    ai_json = {
        "recommendation": recommendation,
        "viability": "Medium",
        "risk_analysis": result["answer"],
        "saturation": "Medium",
        "pricing_strategy": f"Target around KES {market_dict.get('avg_price', 0):,.0f}"
    }
    
    return f"### Lens AI Analysis\n```json\n{json.dumps(ai_json, indent=2)}\n```"
