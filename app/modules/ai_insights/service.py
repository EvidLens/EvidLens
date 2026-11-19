from sqlmodel import Session, select
from typing import Dict, Any
import os
import httpx
from app.core.db import engine
from app.core.models import PriceData, Competitor, Company, MarketMetric, SectorReport, KenyaLensBusiness
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
GROQ_KEY = os.getenv("GROQ_API_KEY")
class AIInsightsService:
    async def generate_insights(self, query: str, market_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        low = (query or "").lower().strip()
        if low in ["hi", "hello", "hey", "niaje", "sasa", "hi!", "hello!", "hey!"]:
            ans = "Hey! I'm Lens, your EvidLens market partner. What business idea are you exploring? Tell me the product and county and I'll pull live prices and competitors for you."
            return {"answer": ans, "reply": ans, "response": ans, "verdict": None, "sources": ["EvidLens"], "chart": {}, "table": []}
        if low in ["i need something", "i need help", "help", "i need", "something", "need something"]:
            ans = "Got you, I'm here. What are you thinking about starting or growing? Just tell me the product or business, even in one word, and I'll take it from there."
            return {"answer": ans, "reply": ans, "response": ans, "verdict": None, "sources": ["EvidLens"], "chart": {}, "table": []}
        sector = market_data.get("sector") or "General"
        county = market_data.get("county") or "Kenya"
        sub_county = market_data.get("sub_county") or market_data.get("subcounty") or ""
        ward = market_data.get("ward") or ""
        budget = market_data.get("budget_kes") or market_data.get("budget") or ""
        prices = []
        competitors = []
        companies = []
        metrics = []
        sector_reports = []
        try:
            with Session(engine) as session:
                q = select(PriceData)
                if county and county != "Kenya":
                    q = q.where(PriceData.county.ilike(f"%{county}%"))
                if sector and sector != "General":
                    q = q.where(PriceData.sector.ilike(f"%{sector}%"))
                prices = list(session.exec(q.limit(10)))
                q2 = select(Competitor)
                if sector != "General":
                    q2 = q2.where(Competitor.sector.ilike(f"%{sector}%"))
                if county != "Kenya":
                    q2 = q2.where(Competitor.county.ilike(f"%{county}%"))
                competitors = list(session.exec(q2.limit(10)))
                q3 = select(Company)
                if sector != "General":
                    q3 = q3.where(Company.sector.ilike(f"%{sector}%"))
                if county != "Kenya":
                    q3 = q3.where(Company.county.ilike(f"%{county}%"))
                companies = list(session.exec(q3.limit(10)))
                q4 = select(MarketMetric)
                if county != "Kenya":
                    q4 = q4.where(MarketMetric.county.ilike(f"%{county}%"))
                metrics = list(session.exec(q4.limit(10)))
                q5 = select(SectorReport)
                if sector != "General":
                    q5 = q5.where(SectorReport.sector.ilike(f"%{sector}%"))
                if county != "Kenya":
                    q5 = q5.where(SectorReport.county.ilike(f"%{county}%"))
                sector_reports = list(session.exec(q5.limit(5)))
        except Exception as e:
            print(f"DB query error: {e}")
        db_context = f"""
LIVE DB (EvidLens 9 Lanes):
PriceData ({len(prices)} rows): {[(p.product_name, p.price, p.county) for p in prices[:5]]}
Competitors ({len(competitors)} rows): {[(c.name, c.county, c.sector) for c in competitors[:5]]}
Companies ({len(companies)} rows): {[(c.name, c.county) for c in companies[:5]]}
MarketMetrics ({len(metrics)} rows): {[(m.product, m.avg_price_kes, m.demand_score, m.county) for m in metrics[:5]]}
SectorReports ({len(sector_reports)} rows): {[(r.sector, r.county, r.market_size_kes, r.growth_rate_percent) for r in sector_reports[:3]]}
Total counts - Prices: {len(prices)}, Competitors: {len(competitors)+len(companies)}, Demand signals: {len(metrics)}
"""
        system_prompt = f"""You are EvidLens Kenya Decision Intelligence - DETAILED ANALYST.
{db_context}
User Query: {query}
Sector: {sector}
County: {county}
SubCounty: {sub_county}
Ward: {ward}
Budget: {budget} KES
If user gave a real business but no county or budget, assume nationwide, KES 500000, 12 months and say you assumed that. Do not block or ask for 4 fields first.
You must give DETAILED 8-section report using REAL DB data above. If DB has 0 rows for a lane, say "No live rows yet - using Kenya benchmark estimate" but still give estimate.
FORMAT:
**1. EXECUTIVE SUMMARY (Go/No-Go Score /10)**
Verdict + Confidence + 2 sentence summary
**2. MARKET SIZE & DEMAND**
- Total Market Size KES (from SectorReport if available else estimate)
- Demand Score /10 (from MarketMetric demand_score if available)
- Monthly Volume units
- Growth % YoY
- Top 3 Products
**3. PRICING INTELLIGENCE (Live KES from PriceData)**
Create table: Product | Avg Price KES | County | Sector | Source
If PriceData has rows, use them. If not, estimate with benchmark.
Include Price Trend: Up/Down %
**4. COMPETITOR LANDSCAPE (Real from Competitor + Company tables)**
List 5 competitors: Name | County | Sector
If 0 rows, say "No competitors in DB yet for this county - market is open" and estimate 3 typical competitors.
Market Concentration: Fragmented/Concentrated
**5. {county} DEEP DIVE**
- Market Size from SectorReport.market_size_kes if exists
- Growth from SectorReport.growth_rate_percent
- Best Subcounty to start (high demand low competition)
- Best Ward
- Population insights
**6. FINANCIAL VIABILITY FOR BUDGET KES {budget or '500,000'}**
- Startup Breakdown: Stock 60%, Rent 20%, Licenses 5%, Transport 10%, Marketing 5% with KES amounts
- Break-even months
- Monthly Revenue KES estimate
- Monthly Profit KES estimate
- ROI % Year 1
- Payback months
**7. RISKS & MITIGATION**
3 Risks with specific mitigation for {county}
**8. 30-DAY ACTION PLAN**
Week 1-4 specific tasks for {county}
Rules: Use KES, counties, subcounties, wards. Cite KNBS, CBK, KRA, and your lanes: PriceData, Competitor, Company, MarketMetric, SectorReport. Minimum 400 words. Never say "Lens error" or "No data yet" without giving estimate. Be DETAILED.
"""
        if GROQ_KEY:
            for model in GROQ_MODELS:
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}, json={"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"DETAILED analysis for {query} in {sector}/{county} {sub_county} Budget KES {budget}. Use real DB rows above."}], "max_tokens": 4000, "temperature": 0.4})
                        if res.status_code == 200:
                            ans = res.json()["choices"][0]["message"]["content"]
                            verdict = "Go"
                            if "No-Go" in ans[:600] or "no-go" in ans[:600].lower():
                                verdict = "No-Go"
                            elif "Needs Research" in ans[:600]:
                                verdict = "Needs Research"
                            return {"answer": ans, "reply": ans, "response": ans, "verdict": verdict, "sources": ["PriceData Lane", "Competitor Lane", "Company Lane", "MarketMetric Lane", "SectorReport Lane", "KNBS", "CBK", f"Groq {model}"], "chart": {"sector": sector, "county": county, "prices": len(prices), "competitors": len(competitors)}, "table": [[c.name, c.sector, c.county] for c in competitors[:5]] + [[c.name, c.sector, c.county] for c in companies[:5]], "map": {"county": county, "prices": len(prices)}}
                        else:
                            print(f"Groq {model} {res.status_code}: {res.text[:400]}")
                except Exception as e:
                    print(f"Groq {model} error {e}")
                    continue
        fallback = f"""**1. EXECUTIVE SUMMARY - {query} in {county}**
Verdict: Go - Opportunity in {sector}
Based on {len(prices)} PriceData rows, {len(competitors)+len(companies)} competitors, {len(metrics)} demand signals in DB. AI is temporarily offline, this is a DB-grounded summary.
**2. MARKET SIZE**
SectorReport shows: {sector_reports[0].market_size_kes if sector_reports else 'No live SectorReport row yet - using Kenya benchmark estimate'} in {county}
Growth: {sector_reports[0].growth_rate_percent if sector_reports and sector_reports[0].growth_rate_percent else 'Estimate 12% YoY - Kenya SME benchmark'}
Demand: {metrics[0].demand_score if metrics else 'Estimate 7/10 - based on county activity'}
**3. PRICING - Live PriceData**
{chr(10).join([f"- {p.product_name}: KES {p.price} in {p.county} ({p.sector})" for p in prices[:5]]) if prices else f"- {query}: No live PriceData row yet in {county} - check Market Prices page for nearest county benchmark"}
**4. COMPETITORS**
{chr(10).join([f"- {c.name} | {c.county} | {c.sector}" for c in competitors[:5]]) if competitors else "- No competitors in DB yet - open market"}
{chr(10).join([f"- {c.name} | {c.county}" for c in companies[:3]]) if companies else ""}
**5. {county} DEEP DIVE**
Best Subcounty: {sub_county or 'Central'} - high footfall
Best Ward: CBD Ward
**6. FINANCIAL BUDGET KES {budget or 500000}**
Break-even 5 months estimate, review with live prices when AI is back
**7. RISKS**
Price, Competition, Seasonality - mitigations provided in full report
**8. ACTION PLAN**
Week1 supplier quotes in {county}, Week2 license, Week3 test, Week4 scale
"""
        return {"answer": fallback, "reply": fallback, "response": fallback, "verdict": "Go", "sources": ["PriceData", "Competitor", "Offline"], "chart": {}, "table": []}
