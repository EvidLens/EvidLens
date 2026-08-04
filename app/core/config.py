from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # APP
    APP_NAME: str = "EvidLens"
    APP_VERSION: str = "1.3.0"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # DATABASE
    DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI BRAIN
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # DATA APIS - EARS
    NEWS_API_KEY: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    X_BEARER_TOKEN: str = ""
    AFRICA_IS_TALKING_API_KEY: str = ""
    AFRICA_IS_TALKING_USERNAME: str = ""

    # DATA APIS - EYES
    GOOGLE_TRENDS_API_KEY: str = ""
    SIMILARWEB_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""

    # PAYMENTS
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_SHORTCODE: str = ""

    # STORAGE
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""

    # CORS - OPEN FOR ALL FOR NOW
    ALLOWED_ORIGINS: List[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()
