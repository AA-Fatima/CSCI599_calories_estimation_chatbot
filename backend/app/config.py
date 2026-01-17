"""Application configuration."""
from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "nutriarab"
    db_user: str = "postgres"
    db_password: str = "postgres"
    migration_batch_size:  int = 100
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # App
    environment: str = "development"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    
    # CORS
    cors_origins: str = "http://localhost:4200"
    allowed_origins: str = "http://localhost:4200"
    
    # Vector Search / Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    similarity_threshold: float = 0.75  # Higher threshold for better precision
    vector_similarity_threshold: float = 0.75  # Higher threshold
    vector_top_k: int = 3
    
    # Admin
    admin_password: str = ""
    
    # Rate Limiting
    rate_limit_per_minute: int = 30
    
    @property
    def database_url(self) -> str:
        """Get async database URL."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def database_url_sync(self) -> str:
        """Get sync database URL (for migrations)."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        origins = self.cors_origins or self.allowed_origins
        return [origin.strip() for origin in origins.split(",") if origin.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
 

settings = get_settings()