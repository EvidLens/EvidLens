import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # APP
    APP_NAME: str = "EvidLens"
    APP_VERSION: str = "1.3.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # DATABASE
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # AI BRAIN
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # DATA APIS - EARS
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY")
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET")
    X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN")
    AFRICA_IS_TALKING_API_KEY: str = os.getenv("AFRICA_IS_TALKING_API_KEY")
    AFRICA_IS_TALKING_USERNAME: str = os.getenv("AFRICA_IS_TALKING_USERNAME")

    # DATA APIS - EYES
    GOOGLE_TRENDS_API_KEY: str = os.getenv("GOOGLE_TRENDS_API_KEY", "")
    SIMILARWEB_API_KEY: str = os.getenv("SIMILARWEB_API_KEY", "")
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # PAYMENTS
    MPESA_CONSUMER_KEY: str = os.getenv("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET: str = os.getenv("MPESA_CONSUMER_SECRET")
    MPESA_PASSKEY: str = os.getenv("MPESA_PASSKEY")
    MPESA_SHORTCODE: str = os.getenv("MPESA_SHORTCODE")

    # STORAGE
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME")

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "https://evidlens-s7x6.onrender.com",
        "http://localhost:8000"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
