from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # APP
    APP_NAME: str = "EvidLens"
    APP_VERSION: str = "1.3.0"
    ENV: str = "prod"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    APP_URL: str = ""

    # DATABASE
    DATABASE_URL: str = ""
    DEV_DATABASE_URL: str = "sqlite:///./evidlens_dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_TOKEN: str = ""

    # AI BRAIN
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-4o-mini"

    # DATA APIS - EARS
    NEWS_API_KEY: str = ""
    X_BEARER_TOKEN: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "EvidLens/1.0"

    # MESSAGING
    AFRICASTALKING_API_KEY: str = ""
    AFRICASTALKING_USERNAME: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # DATA APIS - EYES / LOCATION
    LOCATIONIQ_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

    # PAYMENTS - MPESA
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_CALLBACK_URL: str = ""
    MPESA_ENV: str = "sandbox"
    MPESA_SECURITY_CREDENTIAL: str = ""
    MPESA_INITIATOR_NAME: str = ""

    # DATA SOURCES
    KNBS_API_URL: str = "https://opendata.knbs.or.ke/api"
    OPENFOODFACTS_API_URL: str = "https://world.openfoodfacts.org"
    SERPAPI_KEY: str = ""
    KRA_KEY: str = ""
    CBK_KEY: str = ""
    NBS_KEY: str = ""
    MPESA_KEY: str = ""

    # EMAIL
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@evidlens.co.ke"
    FROM_NAME: str = "EvidLens Kenya"

    # STORAGE
    STORAGE_TYPE: str = "R2"
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "evidlens-reports"

    # SUPABASE AUTH
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    APP_SUPABASE_KEY: str = ""

    # REPORTS
    REPORT_BRAND_NAME: str = "Powered by EvidLens Kenya Sector Data"
    REPORT_LOGO_URL: str = ""

    # CORS - OPEN FOR ALL FOR NOW
    ALLOWED_ORIGINS: List[str] = ["*"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()
