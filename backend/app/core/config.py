"""
Application configuration settings.
All secrets should be loaded from environment variables.
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "PropBase"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/propbase"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # 5 minutes
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # JWT Authentication
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    
    # Apple OAuth
    APPLE_OAUTH_CLIENT_ID: Optional[str] = None
    APPLE_OAUTH_TEAM_ID: Optional[str] = None
    APPLE_OAUTH_KEY_ID: Optional[str] = None
    APPLE_OAUTH_PRIVATE_KEY: Optional[str] = None
    
    # Maps
    MAPBOX_ACCESS_TOKEN: Optional[str] = None
    MAPBOX_STYLE_URL: Optional[str] = None
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    
    # Notion
    NOTION_API_KEY: Optional[str] = None
    NOTION_DATABASE_ID: Optional[str] = None
    
    # amoCRM
    AMOCRM_BASE_URL: Optional[str] = None
    AMOCRM_CLIENT_ID: Optional[str] = None
    AMOCRM_CLIENT_SECRET: Optional[str] = None
    AMOCRM_REDIRECT_URI: Optional[str] = None
    AMOCRM_ACCESS_TOKEN: Optional[str] = None
    AMOCRM_REFRESH_TOKEN: Optional[str] = None
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    TELEGRAM_ALERT_CHAT_ID: Optional[str] = None
    
    # WhatsApp
    WHATSAPP_PROVIDER: str = "meta"  # meta, twilio
    WHATSAPP_API_KEY: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    
    # Yandex Disk
    YANDEX_DISK_OAUTH_TOKEN: Optional[str] = None
    
    # Currency Exchange Rates
    FX_RATES_API_KEY: Optional[str] = None
    FX_RATES_BASE_CURRENCY: str = "USD"
    
    # Email / SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@propbase.com"
    
    # S3 / Object Storage
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET: str = "propbase"
    S3_REGION: str = "us-east-1"
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
