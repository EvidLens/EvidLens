import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_insights(query: str, market_data: dict) -> str:
    """
    Lane 4: AI Insight Generator - Lens
    No DB needed for v1. Just takes query + market_data
    Returns formatted string for dashboard
    """
    sector = market_data.get('sector', 'Unknown')
    county = market_data.get('county', 'Unknown')

    prompt = f"""
    You are Lens, the AI Agent for EvidLens Kenya Decision Intelligence Platform.
    Context: Sector={sector}, County={county}, Query={query}
    Market Data: {json.dumps(market_data)}

    Return ONLY valid JSON with these keys:
    viability, risk_analysis, saturation, pricing_strategy, recommendation.
    Recommendation must be exactly: Go, No-Go, or Needs Research.
    Keep it under 200 words total and be specific to Kenya market.
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        result = chat_completion.choices[0].message.content
        return f"### Lens AI Analysis\n```json\n{result}\n```"

    except Exception as e:
        return f"### Lens AI Temporarily Down\nError: {str(e)}\n\nFallback: Validate demand manually for '{query}' in {county}. Start with 5 customer interviews this week."
