import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class AIInsightsService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async def generate_insights(self, query: str, market_data: dict, user_id: str = None) -> dict:
        sector = market_data.get('sector', 'Unknown')
        county = market_data.get('county', 'Unknown')
        sub_county = market_data.get('sub_county', '')
        ward = market_data.get('ward', '')

        geo = f"{ward}, {sub_county}, {county}, Kenya" if sub_county else f"{county}, Kenya"

        system_prompt = f"""
        You are Ask Lens, the AI Agent for EvidLens. Kenya Decision Intelligence Platform.
        Context: Sector={sector}, Location={geo}
        You have access to 9 Lanes of real-time Kenya data: CBK, KNBS, KRA, eCitizen, KEBS, NSE, Consumer Voice, Market Engine, Location Intel.
        Always cite sources. Always be specific to Kenya counties.
        Return ONLY valid JSON with these exact keys.
        """

        user_prompt = f"""
        Query: {query}
        Return JSON:
        {{
          "answer": "Plain english answer under 200 words",
          "verdict": "Go or No-Go or Needs Research",
          "chart": {{"type": "bar", "labels": [], "data": []}},
          "table": [],
          "map": {{"type": "choropleth", "geo": "{geo}"}},
          "sources": ["KNBS", "CBK"]
        }}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama-3.1-70b-versatile",
                temperature=0.2,
                max_tokens=1200,
                response_format={"type": "json_object"}
            )
            result = chat_completion.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            return {
                "answer": f"Lens is temporarily down. Fallback: Validate demand for '{query}' in {geo} manually.",
                "verdict": "Needs Research",
                "chart": None,
                "table": [],
                "map": None,
                "sources": ["EvidLens Fallback"]
            }
