import os
import requests
import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import Counter
from.models import ConsumerFeedback, SentimentSummary, Sentiment, Source
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

groq_client = Groq(api_key=GROQ_API_KEY)

def get_reddit_token():
    auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": "EvidLens/1.0"}
    res = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
    return res.json().get("access_token")

def fetch_reddit_data(db: Session, sector: str, product_or_topic: str, limit: int = 50) -> int:
    """Fetch posts from Reddit r/Kenya and r/business"""
    token = get_reddit_token()
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "EvidLens/1.0"}

    query = f"{sector} {product_or_topic} Kenya"
    url = f"https://oauth.reddit.com/search?q={query}&limit={limit}&sort=new"
    res = requests.get(url, headers=headers)

    count = 0
    if res.status_code == 200:
        posts = res.json().get("data", {}).get("children", [])
        for post in posts:
            data = post["data"]
            content = f"{data.get('title','')} {data.get('selftext','')}".strip()
            if not content or len(content) < 20:
                continue

            sentiment, score, likes, complaints = analyze_with_groq(content)

            feedback = ConsumerFeedback(
                sector=sector,
                product_or_topic=product_or_topic,
                county="Kenya",
                source=Source.reddit,
                source_url=f"https://reddit.com{data.get('permalink','')}",
                author=data.get("author"),
                content=content[:2000],
                sentiment=sentiment,
                sentiment_score=score,
                likes_mentioned=json.dumps(likes),
                complaints_mentioned=json.dumps(complaints)
            )
            db.add(feedback)
            count += 1

    db.commit()
    return count

def analyze_with_groq(text: str):
    """Use Groq Llama 3.1 70B to extract sentiment, likes, complaints"""
    prompt = f"""
    Analyze this Kenyan consumer comment about a product or business.
    Text: "{text}"

    Return JSON only:
    {{
      "sentiment": "positive|neutral|negative",
      "score": float from -1.0 to 1.0,
      "likes": ["list of things people like"],
      "complaints": ["list of complaints"]
    }}
    """
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        result = json.loads(chat_completion.choices[0].message.content)
        return result.get("sentiment", "neutral"), result.get("score", 0.0), result.get("likes", []), result.get("complaints", [])
    except:
        return Sentiment.neutral, 0.0, [], []

def aggregate_sentiment(db: Session, sector: str, product_or_topic: str, county: str = None):
    """Aggregate feedback and save summary"""
    # 1. Fetch new data
    fetch_reddit_data(db, sector, product_or_topic)

    # 2. Query DB
    query = db.query(ConsumerFeedback).filter(
        ConsumerFeedback.sector == sector,
        ConsumerFeedback.product_or_topic == product_or_topic
    )
    if county:
        query = query.filter(ConsumerFeedback.county == county)

    feedbacks = query.all()

    # 3. Calculate stats
    total = len(feedbacks)
    pos = sum(1 for f in feedbacks if f.sentiment == Sentiment.positive)
    neu = sum(1 for f in feedbacks if f.sentiment == Sentiment.neutral)
    neg = sum(1 for f in feedbacks if f.sentiment == Sentiment.negative)
    avg_score = sum(f.sentiment_score for f in feedbacks) / total if total > 0 else 0.0

    # 4. Extract top likes/complaints
    all_likes = []
    all_complaints = []
    for f in feedbacks:
        all_likes.extend(json.loads(f.likes_mentioned or "[]"))
        all_complaints.extend(json.loads(f.complaints_mentioned or "[]"))

    top_likes = [item for item, count in Counter(all_likes).most_common(5)]
    top_complaints = [item for item, count in Counter(all_complaints).most_common(5)]

    # 5. Save summary
    summary = SentimentSummary(
        sector=sector,
        county=county,
        product_or_topic=product_or_topic,
        total_mentions=total,
        positive_count=pos,
        neutral_count=neu,
        negative_count=neg,
        avg_sentiment_score=avg_score,
        top_likes=json.dumps(top_likes),
        top_complaints=json.dumps(top_complaints)
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return {
        "sector": sector,
        "county": county,
        "product_or_topic": product_or_topic,
        "total_mentions": total,
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "avg_sentiment_score": round(avg_score, 2),
        "top_likes": top_likes,
        "top_complaints": top_complaints
    }
def get_sentiment_summary(data):
    return {"summary": "placeholder"}
