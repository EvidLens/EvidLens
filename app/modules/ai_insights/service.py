import os
import json
from groq import Groq
from dotenv import load_dotenv
from app.modules.db import Session

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_insights(db: Session, query: str, market_data: dict) -> str:
    """
    Lane 4: AI Insight Generator - Lens
    Takes market data and returns AI recommendation string
    """
    sector = market_data.get('sector', 'Unknown')
    county = market_data.get('county', 'Unknown')

    prompt = f"""
    You are Lens, the AI Agent for EvidLens Kenya Decision Intelligence Platform.
    Context: Sector={sector}, County={county}, Query={query}
    Market Data: {json.dumps(market_data)}

    Return JSON with: viability, risk_analysis, saturation, pricing_strategy, recommendation.
    Recommendation must be Go, No-Go, or Needs Research.
    Keep it under 200 words.
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
        # Return as string so it displays in dashboard
        return f"AI Analysis: {result}"

    except Exception as e:
        return f"AI is temporarily down. Fallback: Validate demand manually for {query} in {county}. Start with 5 customer interviews."
