from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import List, Union
import os

class Settings(BaseSettings):
    APP_NAME: str = "EvidLens"
    APP_VERSION: str = "1.3.0"
    ENV: str = "prod"
    DEBUG: bool = False
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    APP_URL: str = ""
    BASE_URL: str = ""
    ADMIN_EMAIL: str = ""
    SUPPORT_EMAIL: str = "support@evidlens.co.ke"
    DPO_EMAIL: str = "dpo@evidlens.co.ke"

    DATABASE_URL: str = ""
    DEV_DATABASE_URL: str = "sqlite:///./evidlens_dev.db"
    REDIS_URL: str = ""
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_TOKEN: str = ""

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL: str = "llama-3.1-8b-instant"

    NEWS_API_KEY: str = ""
    X_BEARER_TOKEN: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "EvidLens/1.0"

    AFRICASTALKING_API_KEY: str = ""
    AFRICASTALKING_USERNAME: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    LOCATIONIQ_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = ""

    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_CALLBACK_URL: str = ""
    MPESA_ENV: str = "production"
    MPESA_SECURITY_CREDENTIAL: str = ""
    MPESA_INITIATOR_NAME: str = ""
    MPESA_BUSINESS_SHORTCODE: str = ""
    MPESA_TRANSACTION_TYPE: str = "CustomerPayBillOnline"

    KNBS_API_URL: str = "https://opendata.knbs.or.ke/api"
    OPENFOODFACTS_API_URL: str = "https://world.openfoodfacts.org"
    SERPAPI_KEY: str = ""

    RESEND_API_KEY: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@evidlens.co.ke"
    FROM_NAME: str = "EvidLens Kenya"

    STORAGE_TYPE: str = "R2"
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "evidlens-reports"

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    REPORT_BRAND_NAME: str = "Powered by EvidLens Kenya Sector Data"
    REPORT_LOGO_URL: str = ""

    SCHEDULER_TIMEZONE: str = "Africa/Nairobi"
    VAT_RATE: float = 0.16

    ALLOWED_ORIGINS: Union[List[str], str] = ["https://app.evidlens.co.ke", "https://evidlens.co.ke"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("ENV", mode="before")
    @classmethod
    def normalize_env(cls, v):
        return str(v).lower() if v else "prod"

    @model_validator(mode="after")
    def validate_production(self):
        is_prod = self.ENV in ("prod", "production")
        if is_prod:
            if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be set to 32+ chars in production")
            if self.SECRET_KEY in ("dev-secret-key-change-me", "change-me", "secret"):
                raise ValueError("SECRET_KEY is still the dev default")
            if not self.DATABASE_URL:
                raise ValueError("DATABASE_URL is required in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("ALLOWED_ORIGINS cannot contain * in production")
        if self.APP_URL and not self.BASE_URL:
            self.BASE_URL = self.APP_URL
        if self.BASE_URL and not self.APP_URL:
            self.APP_URL = self.BASE_URL
        if self.MPESA_SHORTCODE and not self.MPESA_BUSINESS_SHORTCODE:
            self.MPESA_BUSINESS_SHORTCODE = self.MPESA_SHORTCODE
        return self

    @property
    def effective_base_url(self) -> str:
        return (self.BASE_URL or self.APP_URL or "").rstrip("/")

    @property
    def effective_redis_url(self) -> str:
        return self.UPSTASH_REDIS_URL or self.REDIS_URL

    @property
    def is_prod(self) -> bool:
        return self.ENV in ("prod", "production")

settings = Settings()
