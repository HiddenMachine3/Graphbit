from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All sensitive values (SECRET_KEY, DATABASE_URL, etc.) should be 
    stored in a .env file and never committed to version control.
    """
    PROJECT_NAME: str = "NoCodeML API"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # Redis (for Celery)
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour token lifetime

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env

settings = Settings()