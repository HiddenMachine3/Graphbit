from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All sensitive values (SECRET_KEY, DATABASE_URL, etc.) should be 
    stored in a .env file and never committed to version control.
    """
    PROJECT_NAME: str = "GraphBit"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized.startswith("sqlite"):
            raise ValueError("SQLite is disabled. Use PostgreSQL DATABASE_URL.")
        if not (
            normalized.startswith("postgresql://")
            or normalized.startswith("postgresql+")
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL.")
        return value
    
    # JWT Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour token lifetime

    # HuggingFace
    HF_TOKEN: str | None = None
    HF_EMBED_MODEL: str = "BAAI/bge-base-en-v1.5"
    HF_KEYPHRASE_MODEL: str = "ml6team/keyphrase-extraction-distilbert-inspec"

    # Suggestion pipeline defaults
    SUGGESTION_THRESHOLD: float = 0.75
    SUGGESTION_SEMANTIC_WEIGHT: float = 0.6
    SUGGESTION_KEYWORD_WEIGHT: float = 0.4
    SUGGESTION_TOP_K: int = 20
    SUGGESTION_DEDUP_THRESHOLD: float = 0.9

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()