import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_insight(query, sector, county):
    prompt = f"""
You are Lens, the AI Agent for EvidLens Kenya Decision Intelligence Platform.
Context: Sector={sector}, County={county}, Query={query}
Return JSON with: viability, risk_analysis, saturation, pricing_strategy, recommendation.
Recommendation must be Go, No-Go, or Needs Research.
"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        return {"data": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"error": str(e)}
