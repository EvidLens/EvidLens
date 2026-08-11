import os
import requests
import json
from sqlalchemy.orm import Session
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

def extract_county_with_groq(text: str) -> str:
    prompt = f'Extract Kenyan county from this text. If none found return "Kenya". Text: "{text}". Return JSON: {{"county": "County Name"}}'
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content).get("county", "Kenya")
    except:
        return "Kenya"

def fetch_reddit_data(db: Session, sector: str, product_or_topic: str, limit: int = 50) -> int:
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
            permalink = data.get("permalink","")
            source_url = f"https://reddit.com{permalink}"
            exists = db.query(ConsumerFeedback).filter(ConsumerFeedback.source_url == source_url).first()
            if exists:
                continue
            content = f"{data.get('title','')} {data.get('selftext','')}".strip()
            if not content or len(content) < 20:
                continue
            sentiment, score, likes, complaints = analyze_with_groq(content)
            county = extract_county_with_groq(content)
            feedback = ConsumerFeedback(
                sector=sector,
                product_or_topic=product_or_topic,
                county=county,
                source=Source.reddit,
                source_url=source_url,
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
    prompt = f'Analyze this Kenyan consumer comment. Text: "{text}". Return JSON only: {{"sentiment": "positive|neutral|negative", "score": float, "likes": [], "complaints": []}}'
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
    fetch_reddit_data(db, sector, product_or_topic)
    query = db.query(ConsumerFeedback).filter(ConsumerFeedback.sector == sector, ConsumerFeedback.product_or_topic == product_or_topic)
    if county:
        query = query.filter(ConsumerFeedback.county == county)
    feedbacks = query.all()
    total = len(feedbacks)
    pos = sum(1 for f in feedbacks if f.sentiment == Sentiment.positive)
    neu = sum(1 for f in feedbacks if f.sentiment == Sentiment.neutral)
    neg = sum(1 for f in feedbacks if f.sentiment == Sentiment.negative)
    avg_score = sum(f.sentiment_score for f in feedbacks) / total if total > 0 else 0.0
    all_likes = []
    all_complaints = []
    for f in feedbacks:
        all_likes.extend(json.loads(f.likes_mentioned or "[]"))
        all_complaints.extend(json.loads(f.complaints_mentioned or "[]"))
    top_likes = [item for item, count in Counter(all_likes).most_common(5)]
    top_complaints = [item for item, count in Counter(all_complaints).most_common(5)]
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
def get_sentiment_summary(db: Session, sector: str, product_or_topic: str, county: str = None):
    """Wrapper for aggregate_sentiment so market_engine can import it"""
    return aggregate_sentiment(db, sector, product_or_topic, county)
